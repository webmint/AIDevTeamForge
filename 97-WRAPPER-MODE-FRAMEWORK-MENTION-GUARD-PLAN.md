# 97 — Wrapper-Mode Framework-Mention Guard Plan

**Created**: 2026-09-18
**Status**: Phase 0 CLOSED 2026-09-19 by a single blanket maintainer directive (every item AS RECOMMENDED — see `## Phase 0 close record`); Phase 1 DONE 2026-09-19 (three python-engineer → python-reviewer loops, all SHIP-READY after one Low and one Medium test-coverage fix; full `tests/lib` suite 11745 passed); Phase 2 IN PROGRESS 2026-09-19. Drafted 2026-09-18; reviewed three times before ratification (instruction-reviewer: 1 Low, then 1 Medium + 1 Low — all fixed in place; third pass 0 findings); OQ-1 resolved 2026-09-18 via claude-code-guide.

Extend wrapper mode's traceless guarantee from FILES and COMMIT ATTRIBUTION to FILE CONTENT and COMMIT SUBJECTS: in wrapper mode, nothing the framework writes into the client-owned source repo may name a framework artifact or quote its content, and the one permitted reference is the source repo's ticket ID.

---

## Origin & evidence

⚠ **Evidence class, and every summary of this plan must repeat it: TWO maintainer directives given in conversation on 2026-09-18, plus grep-verified structural facts about the tree. No consumer incident was stated, none is claimed, and nothing was measured.** This is a **predicted-gap plan in plan 87's class**. A clean Phase 4 would be evidence that the carriers and the detector behave as designed; it would never be evidence that the gap ever cost anything, because nothing here measured a leak before or after.

**The maintainer's directive, rendered in English as paraphrase** (it was given in Ukrainian; nothing is quoted in the original language, per this repo's English-only file rule):

1. In wrapper mode, forbid code comments from mentioning any framework document or its content — specs and the like.
2. Then generalized: in wrapper mode there must be NO mentions of framework artifacts or their content at all; where a reference is needed, the source repo's ticket number is mentioned.

**Background a reader needs.** "Wrapper mode" is the install shape in which the framework install root — `.devforge/`, `specs/`, `constitution.md`, `CLAUDE.md` — wraps a nested, client-owned product git repo at `PROJECT_ROOT` (the "source repo"). The design promise is recorded in `DEVELOPMENT-STATUS.md` under Key Design Decisions: *"Wrapper mode for client-invisible AI — template wraps around existing project folder; zero Claude traces in the client's repo"*, and plan 25's D5 made the source-repo squash commit traceless. **This plan extends "traceless" from files and commit attribution to file CONTENT and commit SUBJECTS** — the two surfaces the existing guarantee does not reach.

Ten structural facts, each verified against the tree on 2026-09-18. ⚠ Line digits drift — **grep the quoted text, never the digits**.

1. **The traceless guarantee today covers files and commit attribution only.** `src/devforge/lib/_implement/_cmds_verify.py` carries `ISOLATION_ARTIFACTS` — nine path entries (`.claude`, `specs`, `docs/overview.md`, `docs/architecture.md`, `constitution.md`, `CLAUDE.md`, `bugs`, `research`, `.mcp.json`) — checked by `_check_wrapper_isolation(source_root)` ONLY when `workspace.is_wrapper` is True, emitting `{"status": "isolation_failure", "artifacts": [...]}` at exit 2. Plan 25's D5 (`25-FINALIZE-COMMAND-REDESIGN-PLAN.md`, heading *"D5 — Wrapper-mode dual squash; SOURCE repo gets NO AI traces"*) makes the source squash commit `[TICKET-ID] - Description` with no attribution. **Nothing anywhere inspects file CONTENT for framework references.**
2. **No emitted rule forbids naming a framework artifact in code.** A case-insensitive `comment` grep across `src/agents/*.md`, `src/constitution.md` and `src/CLAUDE.md` hits SIX agent files, TWO constitution rules and ONE `src/CLAUDE.md` rule — the enumeration below is exhaustive for all three targets: `tech-writer`'s doc-comment FORMAT guidance; `performance-analyst`'s *"needs an explanatory comment"* advice; `runtime-debugger`'s *"a brief comment only when it is non-obvious"* advice; `ac-verifier` rule 13 (matches confined to comments satisfy a negative-pattern AC); `code-reviewer` check 6's *"no dead code, debug logs, or commented-out blocks"* (dead-code detection); `design-auditor`'s JS-collector placeholder substitution (two hits — *"exactly as its header comment specifies"* and *"per its header comment"*); the constitution's *"Never commit secrets … not in comments"* rule and, under **No dead code**, *"Do not comment them out 'for later.'"*; and `src/CLAUDE.md` `### Always` item 15 *"English in files"*. **None of them restricts naming a framework artifact** — the two added to this enumeration on 2026-09-18 are dead-code detection and placeholder substitution, both unrelated to framework-mention rules.
3. **The constitution's TODO rule offers a leak vector.** `src/constitution.md` §4.2 *NEVER Do [universal]* carries the bullet *"Never leave a TODO without context."*, which explicitly offers *"a reference (ticket number, feature name)"* — **"feature name" is a leak vector in wrapper mode.** §4.2 is a member of `_UNIVERSAL_SECTIONS` in `src/devforge/lib/_constitute/_schema.py`, so any edit there makes `constitute_helper verify-universal-defaults` report drift on every existing install.
4. **The implementing agent's brief is the ONLY channel that knows the mode.** `src/commands/implement/main.md` PHASE 3 already says *"State explicitly that the agent must NOT write forge artifacts (`.claude/`, `specs/`, `CLAUDE.md`, `constitution.md`, `.mcp.json`, `docs/overview.md`, `docs/architecture.md`, `bugs/`, `research/`) into the source tree — those live at the install root."*, and `src/commands/fix/main.md` PHASE 2 carries its twin (*"In wrapper mode, state explicitly that the agent must NOT write forge artifacts … into the source tree"*). A `wrapper` grep across `src/agents/*.md` hits only `frontend-engineer.md`'s *"never modify parent/wrapper elements"* — **NO agent file MENTIONS wrapper mode.** `src/commands/implement/references/agent-brief.md`'s **What NOT to do** bullet is the brief's spec and says nothing about mentions. The PHASE 6 review-panel brief (implement `main.md` PHASE 6 step 1) gives every reviewer *"the `touched_files`, the constitution, and the task body"* — no mode. ⚠ **Amended 2026-09-18 (OQ-1 RESOLVED):** every grep result above is unchanged, and the bolded lead holds for what the ORCHESTRATOR hands a dispatched agent. It does NOT hold for the harness — every subagent also loads the project `CLAUDE.md`, whose `## Wrapper Mode` section is present iff wrapper mode (fact 8), a second channel handed by no one and the signal D3's re-keyed check reads.
5. **The brief hands the engineer the exact vocabulary that leaks.** Implement PHASE 3 names *"the task body … the spec acceptance-criteria slice (`ac_addressed`)"*, and `src/agents/qa-engineer.md` Approach step 1 reads *"Read the spec's acceptance criteria (AC-1, AC-2, …)."* — **the AC label is the natural seed for a test name like `it('AC-3 …')`.**
6. **A mechanical host already exists.** `src/devforge/lib/_verify/_hygiene.py` is a line scanner over changed CODE files (denylist file gate `_is_code_file` over `_SKIP_PATH_SEGMENTS` / `_SKIP_EXTENSIONS`; wrapper-aware `_normalise_path`), emitting `leftover_artifacts` entries `{file, line, kind, snippet}` with kinds `debug_print` / `debug_statement` / `bare_todo` / `bare_fixme` / `commented_code_block`, plus `_TICKET_REF_RE = #\d+|[A-Z]{2,}-\d+|https?://`. It is ADVISORY by plan 34: `_verdict.py` states *"hygiene_flags … NEVER causes NEEDS WORK on its own"* and `_report.py` renders *"Leftover artifacts (advisory — does not block the verdict)"*. **`check-hygiene` (in `_verify/_cli.py`, `cmd_check_hygiene`) takes `--files`, `--scope-baseline`, `--source-root` and NO `--install-root`, so it cannot tell wrapper from standalone**; `resolve-feature-scope` in the same CLI takes both roots and its `--install-root` help reads *"Required for wrapper-mode path prefixing. Default: same as --source-root."*
7. **Source-repo commit subjects in wrapper mode still carry task numbers.** `_implement/_cmds_commit.py` `_compose_message` task mode: wrapper → `"[{0}] - {1} (Task {2})"`, while the fix-mode and final-mode wrapper arms are already `"[{0}] - {1}"` (no suffix). `implement/main.md` PHASE 2 runs `git -C <source_root> commit --allow-empty -m "[checkpoint] pre-task NNN"`. Both are squashed by `/devforge:finalize` on the happy path; both survive on the already-pushed-skip path (plan 25 D9's recorded narrow edge). ⚠ **The `[checkpoint]` PREFIX is LOAD-BEARING**: `_finalize/_preflight.py` `_count_wip_commits` runs in `source_root` grepping `[WIP]` and `[checkpoint]` with `--fixed-strings`, and in wrapper mode the source repo's per-task commits carry no `[WIP]`, so `has_wip_commits` there rests on the `[checkpoint]` commits alone. **The `pre-task NNN` suffix is consumed by nothing** — rollback uses the SHA recorded in `wip.md`, and `_finalize/_squash.py`'s source base is the merge-base scoped to `source_root`, not a grep.
8. **One carrier exists iff wrapper mode.** `src/devforge/lib/_configure/_render.py`'s `_WRAPPER_MODE_TEMPLATE` renders the emitted `CLAUDE.md` `## Wrapper Mode` section, written only when `workspace_mode == "wrapper" and project_root` — **so a rule placed there needs no conditional prose.** Two bounds: **(a)** it is a DERIVED key written into `.devforge/project-config.json` at `/devforge:configure`, and `update.sh` re-substitutes placeholders from that JSON (`configure_helper substitute-file`), so an EXISTING wrapper install sees new template text only after `/devforge:configure` is re-run; **(b)** six preflights (`_review`, `_verify`, `_fix`, `_grill`, `_summarize`, `_finalize`) DETECT wrapper mode by the phrase *"wrapper mode"* or *"wrapper root"* in `CLAUDE.md` — the `## Wrapper Mode` heading supplies it, **so the heading must survive any template edit**. `tests/lib/test_configure_helper.py` pins `"## Wrapper Mode"` in `WRAPPER_MODE_SECTION`.
9. **The pre-commit hook is not a seat for this.** The hook (`/devforge:constitute` Phase 6.4) is copied into `.git/hooks/pre-commit` at the INSTALL root — the wrapper repo, not the source repo — so it cannot enforce anything about source content.
10. **Install-side surfaces are NOT leak surfaces.** The PR body (`finalize/references/results-and-docs.md`: *"the PR is opened against the install/wrapper branch"*), `summary.md`, and `docs/` (`src/CLAUDE.md`: *"All artifacts (`specs/`, `docs/`, `constitution.md`) live in the wrapper root, NOT inside `{{PROJECT_ROOT}}`"*) all live at the install root. **Test names, test descriptions, string literals, identifiers and commit subjects ARE source-side** — they are the surface this plan governs.

---

## Decisions to ratify

Nothing below is ratified. Each item states the decision, its options, a recommendation, and the strongest counter-argument against it, recorded honestly rather than answered away.

### D1 — The rule: what counts as a "mention", and the one permitted reference

**The rule.** In wrapper mode, no content the implementing agents write into the source tree may:

- **(a) NAME a framework artifact** — by path or filename (`specs/…` paths including the feature-dir path `specs/<YYYY>/<MM>/<leaf>/`, `spec.md`, `plan.md`, `tasks/NNN-*.md`, `tasks/README.md`, `constitution.md`, `CLAUDE.md`, `.devforge/`, `.claude/`, `*-handoff.json`, `*-state.json`, `grill.md`, `review.md`, `verification.md`, `summary.md`, `bugs/`, `tickets/`) or by pipeline vocabulary (`Task NNN`, `AC-N`, "acceptance criteria", "spec criteria", "Done When", "constitution", "breakdown", "devforge", `/devforge:*`);
- **(b) QUOTE their content** — AC text, task descriptions, plan decisions, constitution rules.

**Scope of "content":** comments, docstrings, string literals, identifiers, test names / descriptions, and commit subjects. **The ONE permitted reference is the source repo's ticket ID** — the `[A-Z]+-[0-9]+` token `_extract_ticket_id` already reads from the SOURCE branch (`_implement/_cmds_commit.py`). **STANDALONE IS UNTOUCHED:** a single repo legitimately contains these artifacts and may cite them.

**RECOMMEND as stated.**

**Counter-argument, recorded:** the maintainer's first message said "comments" only — narrower and cheaper to enforce. The second message generalized to "no mentions at all", and **a test name or a string literal leaks exactly as a comment does**, so the recommendation is ALL content rather than comments alone. ⚠ **A paraphrase ("as the plan says") is a mention under (b) but is detectable only by judgment (D3), never by the regex (D4).**

### D2 — Instruction carriers (the actual "forbid"; zero gate)

- **(a)** `src/commands/implement/main.md` PHASE 3 gains one wrapper-mode sentence as a SIBLING of the existing must-NOT-write-artifacts sentence (fact 4): the agent must not MENTION them either — no comment, docstring, string literal, identifier or test name may name a framework artifact or quote its content, and where a reference is needed it uses the source branch's ticket ID. `src/commands/fix/main.md` PHASE 2 gains its twin; **PHASE 2 is shared by the feature lane and the cold lane, so one sentence covers both.**
- **(b)** `src/commands/implement/references/agent-brief.md`'s **What NOT to do** bullet gains the wrapper clause. It is the brief's spec, and the `main.md` sentence cites it.
- **(c)** `_WRAPPER_MODE_TEMPLATE` in `_render.py` gains the rule as one or two sentences — a Python string-literal edit plus its test; **the `## Wrapper Mode` heading MUST survive** (fact 8b) — so every wrapper install's `CLAUDE.md` carries it always-on.
- **(d)** **NO builder agent-file edits.** An agent cannot know the mode (fact 4); the brief is the channel, exactly as the existing isolation directive has no agent-file twin. ⚠ **Amended 2026-09-18 (OQ-1 RESOLVED): the decision is unchanged, its reason is narrowed.** A builder agent CAN see the mode — in the `## Wrapper Mode` section of the `CLAUDE.md` it loads at startup — so the reason is no longer that it cannot; it is that **no builder agent file needs to STATE the rule when (a) + (b) + (c) already carry it**, and the existing isolation directive still has no agent-file twin.

**RECOMMEND (a) + (b) + (c) + (d).**

**Counter-argument, recorded:** (c) reaches existing installs only on re-`configure` (fact 8a), so the always-on carrier is absent from every install that does not re-run that command. **Accepted** — (a) arrives via `update.sh`'s command re-emit and is the binding channel; (c) is reinforcement, not the mechanism.

**Amended 2026-09-18 — (c) PROMOTED, (a) KEPT (OQ-1 RESOLVED).** The reasoning above stands and is not withdrawn: it was written while OQ-1 was open, when (c) might have reached the session model alone. **New reasoning, 2026-09-18:** OQ-1 answers YES — every subagent receives the project `CLAUDE.md` at startup — so **(c) is a DIRECT carrier of the rule to every subagent**, the implementing engineers AND the four panel reviewers, not belt-and-braces. **(a) is KEPT for two reasons.** **(1)** Plan 89's D3 recorded the bound that applies to `CLAUDE.md`, in the vendor's own words — *"context, not enforced configuration"*: presence in every session, compliance in none — while the brief is the task-scoped EXPLICIT instruction, exactly as today's must-NOT-write-artifacts directive lives in the brief (fact 4) although `CLAUDE.md`'s wrapper section already states where artifacts live (fact 10). **(2)** Fact 8(a): an EXISTING wrapper install keeps its ORIGINAL `## Wrapper Mode` text until `/devforge:configure` is re-run, so on such an install **the brief sentence is the only carrier of the new rule until then.**

### D3 — Reviewer net: `code-reviewer` check 11, keyed on the `## Wrapper Mode` section

Append check **11 "Framework-mention leak (wrapper mode only)"** to `src/agents/code-reviewer.md`'s Approach list — checks 1–10 keep their numbers, the same append-never-renumber discipline plan 86 used to grow that list from nine to ten. **WHEN the project `CLAUDE.md` in the reviewer's context carries a `## Wrapper Mode` section** — every subagent receives that file at startup (OQ-1) — any comment / docstring / string literal / identifier / test name in the diff that names a framework artifact or quotes its content is **High**: the source repo is client-owned and the only permitted reference is the ticket ID. **When that file carries no `## Wrapper Mode` section, never apply this check, and never infer the mode from paths or from the task body.**

**Amended 2026-09-18 — the trigger is RE-KEYED and the two companion edits are DROPPED (OQ-1 RESOLVED).** As originally drafted, this item keyed the check on the BRIEF (*"WHEN the brief states the project is in wrapper mode"*) and added two companion clauses — implement `main.md` PHASE 6 step 1 (*"Give EACH the same inputs: the `touched_files`, the constitution, and the task body"*) and `fix/main.md` PHASE 4's panel brief — each stating the mode. **That reasoning is recorded, not withdrawn:** with OQ-1 open, the brief was the only channel known to reach a reviewer (fact 4). **New reasoning, 2026-09-18:** OQ-1 answers YES, so the `## Wrapper Mode` section is ALREADY in every reviewer's context without the orchestrator having to remember anything, and it is present on EXISTING wrapper installs too — their section was rendered at their original `/devforge:configure`; only the new rule TEXT waits for a re-configure (fact 8a), while the check's SUBSTANCE lives in the agent file, which `update.sh` re-emits. **One signal, not two** — the same reasoning OQ-3 uses to reject a second way of saying the same thing in one CLI. **Dropped alternative, recorded:** also state the mode in the panel brief. **Its cost:** the check would then depend on an orchestrator clause for a fact the reviewer already holds.

**Why here.** The panel runs PER TASK and its findings MUST be fixed before approve (plan 17 removed `accept anyway`), so this is where the forbid bites at task level — and **an LLM reviewer catches the paraphrases a regex cannot**. Zero gate, zero Python. **Severity High, not Critical**: it is not a constitution rule (D6).

**Counter-argument, recorded and deliberately not answered:** this is an LLM reviewer judging LLM-written comments — **nothing mechanical checks the check** (plan 89 D7's honesty bound), and **Phase 4 is the only place its miss rate is ever observed**.

### D4 — Mechanical detector: a new advisory hygiene kind at `/devforge:verify`, wrapper-only

`_verify/_hygiene.py` gains kind `framework_mention`, scanned over ALL lines of every changed code file (the scanner tracks no quote state — OQ-2), emitted ONLY when the run is wrapper mode. It rides the EXISTING advisory `leftover_artifacts` channel: **`_verdict.py` untouched (never blocks)**, `_report.py`'s render sentence widened to name the new kind.

`check_hygiene(...)` gains an `install_root` parameter and `check-hygiene` an optional `--install-root` (default = source root); **wrapper iff the two realpaths differ — the SAME predicate `resolve-feature-scope` uses in the same CLI** (fact 6, OQ-3). `src/commands/verify/main.md` PHASE 4 passes `--install-root` in wrapper mode, mirroring its PHASE 1 call. **Standalone: no `--install-root` → the kind never fires → byte-identical output.**

**Posture, argued rather than assumed.** Plan 34 DEMOTED hygiene to advisory over false positives; plan 87 shipped its language guard ADVISORY with a named strengthening trigger; **D3 is the per-task bite**, and this is the whole-feature tripwire.

**NAMED STRENGTHENING ARM (not built):** widen `verify-touched`'s wrapper-isolation check so a mention blocks per task under the existing `isolation_failure` handling (`repair` / `skip` / `stop`). **TRIGGER = the first CONFIRMED leak that reached a `/devforge:finalize` squash despite D2 + D3 + D4.**

**Counter-argument, recorded and deliberately not answered:** an advisory line can be ignored, and `/devforge:verify` runs after the per-task WIP commits have already landed in the source repo — locally; the squash rewrites them, so nothing has left the machine.

**Build-time amendment 2026-09-19 (Phase 1), recorded rather than folded in: the `install_root` parameter also RESOLVES paths, closing a pre-existing wrapper-mode defect.** `resolve-feature-scope` emits `files_for_finders` INSTALL-root-relative in wrapper mode (`_shared/feature_scope.py` `_prefix_paths` prefixes each source-relative path with `relpath(source_root, install_root)`), and `/devforge:verify` PHASE 4.2 feeds that array to `check-hygiene --source-root <source_root>`; `check_hygiene` joined every relative path onto `source_root`, so on a wrapper run it read `<source_root>/<prefix>/<path>` — a path that does not exist — and reported every file in `files_unreadable`, while the scope-creep comparison put every file in `scope_creep`. **Without that fix the new kind could never fire on a real wrapper run**, so Phase 1 closed it with the same predicate: when `install_root` is given and differs, a relative changed path carrying the prefix is read from `install_root` and compared to the baseline in its source-relative form; a relative path NOT carrying the prefix, an absolute path, and every standalone call resolve exactly as before, and the reported `file` string is always the input string. Pinned by `TestWrapperPathResolution` (five tests, one documenting the standalone contract). ⚠ A PRE-EXISTING defect of plan 34's wrapper path, found by READING and reproduced in a unit test — never observed on a consumer; it joins this plan's evidence class rather than changing it. ⚠ Until Phase 2 wires `--install-root` into `verify/main.md` PHASE 4.2, the parameter is reachable from no emitted command.

### D5 — The token list, conservative, and its recorded false-positive classes

**Filenames / paths, matched as exact tokens:** `spec.md`, `plan.md`, `specs/`, `tasks/README.md`, `constitution.md`, `CLAUDE.md`, `.devforge`, `.claude/`, `breakdown-handoff`, `research-handoff`, `discover-handoff`, `plan-handoff`, `grill.md`, `verification.md`, `review.md`, `summary.md`, `fix-seed`, `grill-seed`.

**Vocabulary, word-bounded:** `devforge`, `/devforge:`, `Task \d{3}`, `AC-\d+`, `acceptance criteri`, `spec criteria`, `Done When`, `constitution`.

**Deliberately OUT:** bare `spec` / `plan` / `task` / `feature` — ubiquitous in code, and every `*.spec.ts` file would match — and bare `forge`.

**Recorded false-positive classes:** `AC-3` as a Dolby audio codec or an HVAC label; `Task 001` as fixture data in a task-management app; `specs/` as a project's own test directory; "constitution" in a legal-domain app. **Phase 4 is the ONLY place the false-positive rate is observed.**

**RECOMMEND the list as stated**, with the bound that Phase 1 may refine individual regexes but **must keep it a TOKEN list, never a stem match**, and **must record every addition or removal in this D-item**.

**Phase 1 regex decisions, recorded 2026-09-19 (no token added or removed — 26 tokens, 18 filename/path + 8 vocabulary):** filename/path tokens are CASE-SENSITIVE and compiled as `(?<![\w-])<token>` with a trailing `(?![\w-])` for tokens not ending in `/` (so `specs/2026/09/PROJ-7/spec.md` and `.devforge/wip.md` match while `myspecs/`, `my-spec.md` and `cfg.devforge` do not); vocabulary tokens are word-bounded and CASE-INSENSITIVE except `Task \d{3}` and `AC-\d+`, which keep their case (`task 001` / `ac-3` are not the label shapes). ONE refinement beyond a literal reading: `devforge` is compiled as `(?<![\w.-])devforge(?![\w-])`, because a bare `\b` treats `.` as a boundary and would fire inside `cfg.devforge` — `.devforge/` is still caught by its own filename token and `/devforge:` by its own. Two further false-positive INSTANCES were probed at review and recorded in the module docstring beside the four classes: a test name `it('AC-3 paginates')` and a string literal `"specs/"` both match by design (no quote state; test names are content). Findings are ADDITIVE to the five existing kinds — a line can carry one existing-kind finding and one `framework_mention`, existing-kind first — with at most one mention per line.

### D6 — NO constitution edit

The §4.2 TODO bullet's *"(ticket number, feature name)"* stays byte-identical. **The wrapper carriers (D2) NARROW the offered choice to the ticket number in wrapper mode — narrowing an option a law offers is not a contradiction with it.**

**Why.** §4.2 is universal (fact 3), so an edit produces a drift finding on every consumer. Plans 86 and 89 accepted that cost for UNIVERSAL rules; **this rule is mode-specific and does not belong in a mode-agnostic law.**

**Counter-argument, recorded:** a reader of the constitution alone still sees "feature name" offered. **Accepted** — the brief is what the agent acts on.

### D7 — Source-repo commit subjects lose their task numbers (wrapper only)

- **(a)** `_compose_message`'s task-mode wrapper arm → `"[{0}] - {1}"`, making the wrapper arm IDENTICAL across task / fix / final modes (fact 7). Blast radius: one `format` line; `_implement/_cli.py`'s `wip-commit` help text; the `_cmds_commit.py` module + function docstrings; six test sites in `tests/lib/_implement/test_cmds_commit.py` — grep `(Task 0` beside a `[A-Z]+-\d+]` ticket. **Standalone `"[WIP] task: {0} (Task {1})"` is byte-unchanged.**
- **(b)** implement `main.md` PHASE 2's wrapper checkpoint becomes `[checkpoint]` with NO `pre-task NNN`. **The `[checkpoint]` prefix is KEPT** because `/devforge:finalize`'s `has_wip_commits` in wrapper mode rests on it (fact 7). **Standalone keeps `[checkpoint] pre-task NNN`.**

**Both (a) and (b) close the already-pushed edge ONLY** — plan 25 D9's recorded narrow edge — and **the squash already erases them on the happy path**. Say both things wherever this is summarized.

**RECOMMEND (a) + (b).** **Alternative recorded:** leave both, which is cheaper — but then the guarantee depends on the squash succeeding, which is the very reasoning plan 25 used to recommend its Phase 6.

**Honest bound:** `<title>` — the task title in task mode, the bug/finding title in fix mode — lands in the source subject UNSCANNED. **A task titled "Implement AC-3 pagination" leaks through the subject**; Phase 4 observes it, nothing mechanizes it.

### D8 — Tripwires and non-deltas

No new gate, no new `verify-*` number, no hard-fail validator (**plan 75's tripwire, both halves**); no new config key; **no plan-63/93 count delta** (no `disable-model-invocation` flag moves); no back-port into shipped installs — command specs and agents arrive via `update.sh`, and the `CLAUDE.md` section only on re-`configure` (fact 8a); **standalone behavior byte-identical at every seat.**

### OQ-1 — Does the emitted `CLAUDE.md` reach subagents? — RESOLVED 2026-09-18: YES

**The question as asked:** if Claude Code loads the project `CLAUDE.md` into subagent context, **D2(c) also binds engineers directly**; if not, only the session model sees it and **D2(a) is the sole engineer channel**. **Either answer ships D2(a) + (c);** the answer decides how D2(c) is described and what D3's check keys on.

**Checked on 2026-09-18 through the `claude-code-guide` agent** — this repo's rule routes every Claude-Code-integration fact through that agent and never from memory. The agent fetched `https://code.claude.com/docs/en/sub-agents.md`; its startup-context section (headed *"What Loads at Startup"* as the page read that day) lists what a non-fork subagent's initial context contains, including:

> **CLAUDE.md files**: every level of the CLAUDE.md hierarchy the main conversation loads, including `~/.claude/CLAUDE.md`, project rules, `CLAUDE.local.md`, and managed policy files. The built-in Explore and Plan agents skip this. A subagent whose definition sets `omitClaudeMd` loads only the managed policy files, or none at all when the definition comes from managed settings.

Three further facts from that check: **(i)** the only agents the page exempts are the BUILT-IN Explore and Plan agents, and the agents these carriers must reach — the implementing engineers and the four panel reviewers — are custom `.claude/agents/*.md` agents emitted from `src/agents/`, so none of them is exempt; **(ii)** the ONLY control is the optional agent-frontmatter key `omitClaudeMd`, which suppresses the load; **(iii)** the docs are explicit on this, not ambiguous. Tree check the same day: `grep -rn omitClaudeMd src/ scripts/` returns ZERO hits, **so every one of the 19 agent sources in `src/agents/` receives the project `CLAUDE.md`.**

**Consequences, both recorded at their decision:** D2(c) is PROMOTED to a direct carrier and D2(a) is kept for two named reasons (see D2's dated amendment); D3's check is RE-KEYED onto the `## Wrapper Mode` section and its two panel-brief companion edits are DROPPED (see D3's dated amendment).

⚠ **OQ-1 is NO LONGER a Phase-2 precondition** — it is answered, and Phase 2 starts with no `claude-code-guide` check owed.

**Bound:** a docs-page fact is DATED. If that page changes, **re-verify through `claude-code-guide`, never from memory.**

### OQ-2 — Scan all lines or comment lines only?

**RECOMMEND ALL lines.** D1 says any mention; the scanner tracks no quote state anyway (fact 6); a string literal or a test name is a mention.

### OQ-3 — Wrapper predicate for `check-hygiene`

**RECOMMEND `--install-root` realpath inequality**, mirroring `resolve-feature-scope` in the same CLI (fact 6). **Reject a separate `--wrapper-mode` boolean** — a second way to say the same thing in one CLI.

### OQ-4 — Also surface mentions per task on `verify-touched`'s `pass` payload?

**RECOMMEND NO for v1.** D3's panel check is the per-task net; a second per-task channel duplicates it and changes a helper contract `/devforge:fix` also consumes. **Record it as the first step of D4's strengthening path.**

### OQ-5 — `tech-writer` / `/devforge:finalize` — any edit?

**RECOMMEND NO-OP, verified:** `tech-writer`'s inline doc-comment role is VERIFICATION only (*"the implementing agent authors inline docs"*), and `docs/` is install-side (fact 10).

### OQ-6 — `/devforge:fix` cold lane and the bug title

D2(a) covers both lanes — PHASE 2 is shared (fact 4). The cold commit's `<title>` is the bug title; **bug files are install-side, but the TITLE lands in the source subject.** Bound recorded under D7, **not mechanized**.

---

## Phase 0 close record

**CLOSED 2026-09-19 by a single blanket maintainer directive** — given in Ukrainian as the first message of the build session; English paraphrase: *"implement 97"*. **Every ratifiable item is ratified AS RECOMMENDED. No per-item deliberation was supplied**, and this record does not imply that any counter-argument was answered — each stays recorded at its decision (the plans 91 / 92 / 94 / 95 / 96 / 98 precedent). The orchestrator stated this reading of the directive to the maintainer at build start, naming it as its own interpretation, and proceeded under the autonomous-build convention.

- **D1** — RATIFIED as recommended: ALL content (comments, docstrings, string literals, identifiers, test names / descriptions, commit subjects); the source branch's ticket ID is the ONE permitted reference; standalone untouched; paraphrase is a mention detectable by judgment only.
- **D2** — RATIFIED as recommended: (a) + (b) + (c) + (d), with the dated 2026-09-18 amendment standing — (c) is a DIRECT carrier to every subagent and (a) is KEPT for its two named reasons.
- **D3** — RATIFIED as recommended: `code-reviewer` check 11, High, keyed on the `## Wrapper Mode` section in the reviewer's own context; the two panel-brief companion edits stay DROPPED.
- **D4** — RATIFIED as recommended: advisory `framework_mention` kind on the existing `leftover_artifacts` channel, wrapper-only, `_verdict.py` untouched; the strengthening arm recorded, not built. ⚠ *Build-time amendment 2026-09-19, recorded at D4 below: the same `install_root` parameter also resolves the install-root-prefixed changed paths, closing a pre-existing wrapper-mode read defect without which the kind could never fire.*
- **D5** — RATIFIED as recommended: the token list as stated, kept a TOKEN list; Phase 1's regex refinements are recorded at D5 below.
- **D6** — RATIFIED: NO constitution edit; §4.2 byte-identical.
- **D7** — RATIFIED as recommended: (a) + (b); the `[checkpoint]` prefix KEPT; the `<title>` bound recorded, not mechanized.
- **D8** — RATIFIED as recommended: no gate, no `verify-*` number, no validator, no config key, no 16/4 delta, no back-port, standalone byte-identical.
- **OQ-1** — RESOLVED 2026-09-18 through the `claude-code-guide` agent, before ratification and outside it — a recorded fact, not a ratified arm; nothing about it is owed after this close.
- **OQ-2** — ALL lines.
- **OQ-3** — `--install-root` realpath inequality, mirroring `resolve-feature-scope`; no `--wrapper-mode` boolean.
- **OQ-4** — NO for v1; recorded as the first step of D4's strengthening path.
- **OQ-5** — NO-OP, verified.
- **OQ-6** — D2(a) covers both `/devforge:fix` lanes; the bug-title bound stays under D7, not mechanized.

---

## Phases

### Phase 0 — Ratification

Every D-item (D1–D8) and every OQ (OQ-1–OQ-6) above gets a recorded outcome in `## Phase 0 close record`. **No build until Phase 0 is closed.** Record OQ-1's status explicitly: it was RESOLVED on 2026-09-18 through the `claude-code-guide` agent, before ratification and outside it — **not a ratification fork, and nothing about it is owed after the close.** Its consequences ARE ratifiable: D2's and D3's dated amendments.

#### Verify

- `## Phase 0 close record` names **each** of D1–D8 and OQ-1–OQ-6 with its ratified arm — no item silently omitted. **OQ-1's entry records it as RESOLVED 2026-09-18, not as a ratified arm.**
- The record states whether per-item deliberation was supplied.
- Each decision above still carries its counter-argument. **A ratified decision with its counter-argument deleted cannot be re-opened honestly.**

### Phase 1 — Python

**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn** (house discipline).

1. **`_verify/_hygiene.py`** — kind `framework_mention` over the D5 token list; `install_root` parameter on `check_hygiene`; the wrapper predicate (OQ-3). **`_verify/_cli.py`** — `--install-root` on `check-hygiene`, optional, default `None` → source root. **`_verify/_report.py`** — the render sentence names the new kind. ⚠ **`_verdict.py` is NOT touched** (D4).
2. **`_implement/_cmds_commit.py`** — D7(a); plus `_implement/_cli.py`'s `wip-commit` help text, the module + function docstrings, and the six test sites (fact 7). **The fix-mode and final-mode tests asserting no `(Task NNN)` stay green.**
3. **`_configure/_render.py`** — the `_WRAPPER_MODE_TEMPLATE` sentence(s) of D2(c).

**Tests.** Standalone (no `install_root`) → the kind never appears and **every pre-existing assertion still holds**. Wrapper → each D5 token flagged on a planted line carrying `file` / `line` / `kind` / `snippet`. The ticket-only line `// TODO(PROJ-7): …` **NOT flagged**. **Each recorded false-positive class (D5) is exercised and ASSERTED AS FLAGGED** — documented, not argued away, so the advisory posture is visible in the suite. `_is_code_file`'s gate still skips prose. For (3): a test asserting the rule text is present, `"## Wrapper Mode"` retained (fact 8b), and `{project_root}` still substituted.

#### Verify

- `python -m pytest tests/lib/_verify tests/lib/_implement tests/lib/test_configure_helper.py -q` green, then the **full `tests/lib` suite** green.
- `grep -n "framework_mention" src/devforge/lib/_verify/_hygiene.py src/devforge/lib/_verify/_report.py` hits **both** files.
- `grep -n "install_root" src/devforge/lib/_verify/_cli.py` shows the new optional argument on `check-hygiene`.
- `_verdict.py` is byte-unchanged — capture its pre-change state and confirm.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — Instructions

**Route: instruction-author → instruction-reviewer.** OQ-1 is RESOLVED (2026-09-18), so this phase has **no `claude-code-guide` precondition**.

- **`src/commands/implement/main.md`** — the PHASE 3 sentence (D2a); the PHASE 2 wrapper checkpoint (D7b: the block today reads `git -C <source_root> commit --allow-empty -m "[checkpoint] pre-task NNN"` and must become mode-split); the `## Outputs of this phase` lines naming `(Task NNN)` and `[checkpoint] pre-task NNN` (D7). **PHASE 6 step 1 is NOT edited** — D3's companion clause was dropped 2026-09-18.
- **`src/commands/fix/main.md`** — the PHASE 2 sentence (D2a); **verify at build** whether its `## Outputs` lines naming the wrapper commit shape change at all — the fix-mode and final-mode wrapper shapes are already suffix-free (fact 7). **PHASE 4's panel brief is NOT edited** — D3's companion clause was dropped 2026-09-18.
- **`src/commands/implement/references/agent-brief.md`** — the **What NOT to do** bullet (D2b).
- **`src/agents/code-reviewer.md`** — check 11 (D3), following `src/agents-AUTHORING.md`: numbered Approach list, unified severity, **the fenced `yaml` meta-block byte-unchanged, `tools:` unchanged.**
- **`src/commands/verify/main.md`** — the PHASE 4 `check-hygiene` call gains `[--install-root <install-root>  # wrapper mode only]` and the surrounding paragraph names the new advisory kind. **The scratch-file list line for `hygiene.json` needs NO key change** — the kind lives inside `leftover_artifacts`.
- **`src/commands/implement/references/crash-recovery.md`** — **edited UNCONDITIONALLY.** Verified 2026-09-18: its opening paragraph names the artefact as *"the per-task empty checkpoint commit (`[checkpoint] pre-task NNN`, PHASE 2 — created in the **source** repo)"*. Mode-split that sentence the way the PHASE 2 checkpoint block is split (D7b) — standalone `[checkpoint] pre-task NNN`, wrapper `[checkpoint]`.

#### Verify

- `grep -rn "pre-task NNN" src/` returns **only standalone-arm sites**.
- `grep -n "must NOT mention\|must not mention" src/commands/implement/main.md src/commands/fix/main.md` hits **both** files.
- `grep -n "^11\. \*\*" src/agents/code-reviewer.md` hits, and checks 1–10 are byte-unchanged.
- `grep -n "Wrapper Mode" src/agents/code-reviewer.md` hits — check 11 names the section it keys on (D3).
- `grep -n "install-root" src/commands/verify/main.md` shows the PHASE 4 call.
- The `code-reviewer` check names its own precondition — **it applies only when the project `CLAUDE.md` in its context carries a `## Wrapper Mode` section, and never infers the mode from paths or from the task body** (D3).
- **The two dropped companion edits did not land:** implement `main.md` PHASE 6 step 1 and `fix/main.md` PHASE 4's panel brief are byte-unchanged (D3, amended 2026-09-18).
- **No plan vocabulary in emitted text.** "D1", "D7", "Phase 2" and this plan's number are maintainer vocabulary; emitted text names only the rule, the command and the flag.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 3 — Docs sweep

**Route: instruction-author → instruction-reviewer** for every `src/` and plan-document edit.

- **`CHANGELOG.md`** — this phase **CREATES** the `## [Unreleased]` section above the top entry and writes the plan's entry into it. Verified 2026-09-18: the file carries **no** `## [Unreleased]` section and its top entry is `## [2.0.11] - 2026-09-18`.
- **`DEVELOPMENT-STATUS.md`** `### Wrapper Mode` bullets — one new bullet for the content-level guard and the commit-subject change.
- **Repo `CLAUDE.md`** "Currently active" index one-liner + **`PLAN-STATUS-ARCHIVE.md`** entry. ⚠ The one-liner is added at DRAFT time by the orchestrator, not by this phase; **this phase updates it to the DONE shape.**
- **Dated in-place forward notes, one sentence each, never a rewrite:** plan 25 D5 (`25-FINALIZE-COMMAND-REDESIGN-PLAN.md`, at the D5 heading) — content + subject traces are plan 97's; plan 13 (`13-IMPLEMENT-WRAPPER-MODE-PLAN.md`) — the file-level isolation check gained a content-level sibling in plan 97.
- **`README.md`** — **NO edit; verified no-op 2026-09-18.** It does not state the traceless promise — `traceless` and *"zero Claude traces"* both return zero hits — so there is no clause to amend. Recorded here rather than dropped, per this phase's Verify.

#### Verify

- `grep -n "97" CHANGELOG.md DEVELOPMENT-STATUS.md CLAUDE.md PLAN-STATUS-ARCHIVE.md 25-FINALIZE-COMMAND-REDESIGN-PLAN.md 13-IMPLEMENT-WRAPPER-MODE-PLAN.md` shows the plan number at each site this phase edited.
- The `CHANGELOG.md` entry states the honest bound: **an advisory detector plus instruction carriers plus one reviewer check — NOT a guarantee that no mention reaches the source repo.**
- Each checked site is recorded as an **edit or an explicit verified no-op** — an unrecorded no-op is indistinguishable from an unchecked site.
- The plan-96 index one-liner is byte-unchanged; the plan-97 one-liner is an append.

### Phase 4 — Consumer e2e — DEFERRED, user-driven HARD GATE, NOT run

**Everything above is build-verified, NOT consumer-validated. "Done" never means Phase 4 passed.** Known-answer anchors, all in a WRAPPER install:

1. **The leak case.** A planted comment `// per specs/2026/09/PROJ-7/spec.md AC-3` in one task → `code-reviewer` **High** at PHASE 6 (must be fixed before approve) **AND** a `framework_mention` entry in `/devforge:verify`'s hygiene output.
2. **The legitimate case.** A `// AC-3 audio track` comment in the same run → **NOT flagged by the reviewer.** ⚠ **The regex WILL flag it** — that is D5's recorded false-positive class and the reason for D4's advisory posture. **Record it as a NUMBER, not as a failure.**
3. **The permitted reference.** `// TODO(PROJ-7): …` passes **both** the reviewer and the detector.
4. **Commit subjects.** The source WIP subject reads `[PROJ-7] - <title>` with **no `(Task NNN)`**, the checkpoint reads `[checkpoint]`, and `/devforge:finalize`'s preflight still reports `has_wip_commits: true` (fact 7).
5. **Standalone.** A STANDALONE run → **zero behavioral diff**: no `framework_mention` kind, subjects unchanged.

⚠ **Anchors 1 and 2 are scored as a PAIR** — a reviewer that flags everything passes 1 and fails 2, so anchor 1 alone proves nothing.

#### Verify

- All five anchors are scored **explicitly** — stated, not summarized.
- Anchor 2's regex hit is recorded as a COUNT alongside the reviewer's verdict on it.
- **If it fails**, record the negative with the artifacts and identify which mechanism produced it before proposing anything: a missed leak in anchor 1 is a D3 or D5 finding, a reviewer flag in anchor 2 is a D3 finding, a blocked run anywhere is a D4 posture finding (the advisory leaked into the verdict). **They have different fixes.**
- **A clean run is NOT evidence the guard works** — it is evidence the carriers and detector behave on planted input. **D4's strengthening trigger is an observed leak, and this phase cannot produce one.**

---

## Non-goals

- **Standalone behavior.** Untouched at every seat; a standalone repo legitimately contains and may cite framework artifacts.
- **Any gate, any `verify-*` number, any hard-fail validator.** Plan 75's tripwire, both halves.
- **Scanning commit `<title>`s.** The bound is recorded under D7, not mechanized.
- **A constitution edit.** D6; §4.2 stays byte-identical.
- **Builder agent-file edits.** D2(d); no agent FILE mentions the mode (fact 4) and none needs to — (a) + (b) + (c) carry the rule. `code-reviewer`'s check 11 is a REVIEWER edit gated on the `## Wrapper Mode` section in its own context (D3), not a builder edit.
- **Panel-brief mode clauses.** D3's two companion edits were DROPPED on 2026-09-18 — implement `main.md` PHASE 6 step 1 and `fix/main.md` PHASE 4's panel brief stay byte-unchanged.
- **A new config key.** D8.
- **Back-porting into shipped installs.** Command specs and agents arrive via `update.sh`; the `CLAUDE.md` section only on re-`configure` (fact 8a).
- **Scanning install-side surfaces** — `docs/`, `summary.md`, the PR body (fact 10).
- **Paraphrase detection by regex.** D1's counter-argument names it as judgment-only; D3 is the only net that reaches it.
- **The Cyrillic language guard's path** — `artifact_helper commit-artifacts`, plan 87. A different repo and a different concern.
- **Mechanizing D3's reviewer check.** Nothing verifies the check; that bound is stated, not closed.

---

## Context for next session

The compressed fact base, so a fresh session need not re-derive it. ⚠ **All line digits drift — grep the quoted text.**

**The one sentence that governs everything here:** wrapper mode's traceless promise is enforced today over FILES and COMMIT ATTRIBUTION only (fact 1), and this plan adds CONTENT and SUBJECTS through three instruction carriers, one reviewer check and one advisory detector — **none of which is a gate.**

**Trap 1 — dropping the `[checkpoint]` prefix along with `pre-task NNN`** (fact 7). `_finalize/_preflight.py`'s `_count_wip_commits` greps `[WIP]` and `[checkpoint]` with `--fixed-strings` in `source_root`, and wrapper-mode per-task commits carry no `[WIP]`, so **`has_wip_commits` there rests on `[checkpoint]` alone.** D7(b) removes the suffix and keeps the prefix; removing both breaks finalize's preflight silently. The suffix itself is consumed by nothing — rollback uses the SHA in `wip.md` and the squash base is a merge-base.

**Trap 2 — believing D2(c) reaches existing installs** (fact 8a). `## Wrapper Mode` is rendered from a DERIVED config key at `/devforge:configure`, and `update.sh` re-substitutes from `.devforge/project-config.json`, so an existing wrapper install sees the new sentence only after re-running `/devforge:configure`. **On such an install D2(a) is the only carrier of the new rule.** ⚠ **Amended 2026-09-18:** where the new text IS rendered, (c) is a DIRECT carrier reaching every subagent (OQ-1) — the earlier *"reinforcement, not the mechanism"* framing was written while OQ-1 was open. What this trap guards is unchanged: on an install that has not re-run `/devforge:configure`, the section still carries the OLD text.

**Trap 3 — editing `_WRAPPER_MODE_TEMPLATE` past its heading** (fact 8b). Six preflights detect wrapper mode by finding *"wrapper mode"* or *"wrapper root"* in `CLAUDE.md`, and `tests/lib/test_configure_helper.py` pins `"## Wrapper Mode"`. **A template edit that moves or renames the heading disables wrapper detection in six commands.**

**Trap 4 — making the detector block.** D4 rides the EXISTING advisory `leftover_artifacts` channel and `_verdict.py` is untouched (fact 6). Plan 34 demoted this exact channel to advisory over false positives, and D5 records four legitimate false-positive classes. **A detector wired into the verdict is the fail-closed defect D4 refuses, arriving by wiring rather than by decision.**

**Trap 5 — inferring wrapper mode in an agent.** No agent FILE mentions the mode (fact 4). D3's check 11 fires only when the project `CLAUDE.md` in the reviewer's context carries a `## Wrapper Mode` section (OQ-1, and the trigger was re-keyed onto it on 2026-09-18); **an agent that infers the mode from a path or from the task body will be wrong in standalone and will flag legitimate citations.**

**Trap 6 — reading a clean Phase 4 as validation.** Nothing here has ever observed a leak. D4's strengthening trigger is a confirmed leak past all three layers, and Phase 4 cannot produce one.

**Build order, and it is forced rather than preferred:** **Phase 1 (Python) first** — Phase 2's `verify/main.md` edit names a flag that must exist, and its `implement/main.md` PHASE-2 edit describes a commit shape Phase 1 changes. **OQ-1 is RESOLVED (2026-09-18), so Phase 2 has no precondition beyond Phase 1.** Phase 3 is last because it records what the earlier phases actually did.

**File anchors:**

- `src/devforge/lib/_verify/_hygiene.py` — `_is_code_file`, `_SKIP_PATH_SEGMENTS`, `_SKIP_EXTENSIONS`, `_normalise_path`, `_TICKET_REF_RE`; the five existing kinds.
- `src/devforge/lib/_verify/_cli.py` — `cmd_check_hygiene` (`--files` / `--scope-baseline` / `--source-root`) and `resolve-feature-scope` (both roots; its `--install-root` help is the predicate D4 mirrors).
- `src/devforge/lib/_implement/_cmds_commit.py` — `_compose_message`, `_extract_ticket_id`; `src/devforge/lib/_implement/_cmds_verify.py` — `ISOLATION_ARTIFACTS`, `_check_wrapper_isolation`.
- `src/devforge/lib/_configure/_render.py` — `_WRAPPER_MODE_TEMPLATE`; `tests/lib/test_configure_helper.py` — `WRAPPER_MODE_SECTION`.
- `src/devforge/lib/_finalize/_preflight.py` — `_count_wip_commits`; `src/devforge/lib/_finalize/_squash.py` — the merge-base source base.
- `src/commands/implement/main.md` — PHASE 2 (checkpoint), PHASE 3 (the brief + the isolation sentence), `## Outputs of this phase`; PHASE 6 step 1 (panel inputs) — **read-only here** (D3's companion edit was dropped); `references/agent-brief.md` (**What NOT to do**); `references/crash-recovery.md` (its opening paragraph names `[checkpoint] pre-task NNN`).
- `src/commands/fix/main.md` — PHASE 2 (shared by both lanes); PHASE 4 (panel brief) — **read-only here** (D3).
- `src/agents/code-reviewer.md` — the ten-item Approach list; `src/agents-AUTHORING.md` — the skeleton it must follow.
- `src/constitution.md` §4.2 and `src/devforge/lib/_constitute/_schema.py`'s `_UNIVERSAL_SECTIONS` — **read-only here** (D6).

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context not in the conversation.
2. **Check `## Phase 0 close record` first.** If it still reads *Pending*, nothing is ratified and **no build phase may start**.
3. **Read the live files before editing.** Line digits in this document drift; **grep the quoted text, never the digits** — `ISOLATION_ARTIFACTS`, `_check_wrapper_isolation`, `_compose_message`, `[checkpoint]`, `_count_wip_commits`, `_WRAPPER_MODE_TEMPLATE`, `## Wrapper Mode`, `leftover_artifacts`, `advisory — does not block the verdict`.
4. **Route every edit through the house flow** — instruction-author → instruction-reviewer for every markdown edit, python-engineer → python-reviewer for every Python edit, and **`claude-code-guide` for every Claude-Code-integration fact**. OQ-1 is already RESOLVED (2026-09-18) and owes no re-check unless the docs page it cites changes.
5. **Commit by explicit path, never `git add -A`.** Another session may be mid-build in the same checkout; hold ledger and `main.md` sweeps until it commits.
6. **After each phase, cross-check**: grep every identifier, path, flag name and section number touched, and fix dangling references in the SAME change.
7. **Keep the evidence class attached.** Any summary of this plan repeats that it is a predicted-gap plan — two maintainer directives plus grep-verified structure, **no consumer incident, nothing measured.**
