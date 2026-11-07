# 131 — Consumer Lessons Triage Plan

**Created**: 2026-10-05
**Status**: **Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start. Nothing is built and nothing is measured.** Every decision (D1–D18) and every open question from OQ-2 to OQ-8 carries a recommendation, every decision carries its strongest counter-argument, and each waits for the maintainer; OQ-1 is answered by the tree. ⚠ **Evidence class, repeated in every summary of this plan: ONE consumer installation; the lessons are that installation's memory as consolidated by a sibling session; NOTHING in them re-verified against the 2.0 tree by the sender; the 2.0 tree VERIFIED here by grep and read on 2026-10-05; NOTHING built and NOTHING measured by this plan. Numbers quoted inside lessons or the handoff ("12 of 52 paths", "6 → 34", "23 of 26 sites", "≈300 → 20 calls", "354 entries / 259 KB") are illustrations from that installation, not benchmarks.** ⚠ **Sequencing.** Plans execute in NUMERIC ORDER (D17). On 2026-10-05 plans 112–124 and 126–130 are open ahead of this one, and 125 is DONE (build) with its Phase 4 not run. **Plan 128 builds BEFORE 131 and edits the same files** — `src/commands/verify/main.md`, `src/commands/specify/main.md` Step 4.4, `src/commands/verify/references/report-format.md`, `_verify/_verdict.py`, `_verify/_report.py` and `_verify/_cli.py`'s registry — so every anchor below drifts by build time. ⚠ **Numbered 131 because a glob of `13[1-9]-*.md` at the repo root on 2026-10-05 returns nothing. Other sessions work in this checkout and may take 131 first; a resuming session re-checks the number before trusting it.** ⚠ **Every `file:line` here was read on 2026-10-05 and will drift — grep the quoted text, never the digits.**
**Branch:** `develop-2.0-init`

On 2026-10-05 a sibling session handed over 54 portable lessons distilled from one consumer installation's project memory. **This plan triages every one of them against the 2.0 tree** — covered by 2.0 (the mechanism cited), covered by plan 128, a decision here for a command / helper / agent / template, a `FINDINGS.md` entry with no owner, or consumer-only and left out — **and proposes decisions D1–D18 for the gaps.** It re-opens nothing plan 128 decides (`## Overlap with plan 128`), and it creates no stack reference file (D18).

---

## Origin & evidence

⚠ **Evidence class, stated first and repeated in every summary of this plan: ONE consumer installation; the lessons are that installation's memory as consolidated by a sibling session; NOTHING in them re-verified against the 2.0 tree by the sender; the 2.0 tree VERIFIED here by grep and read on 2026-10-05; NOTHING built and NOTHING measured by this plan. Numbers quoted inside lessons or the handoff ("12 of 52 paths", "6 → 34", "23 of 26 sites", "≈300 → 20 calls", "354 entries / 259 KB") are illustrations from that installation, not benchmarks.**

On 2026-10-05 a sibling session sent a cross-session handoff: **54 portable lessons** distilled from ONE consumer installation's project memory. The installation runs in wrapper mode on the 1.x command layout and carries six months of specs (April–October 2026). Its memory was consolidated on 2026-10-05 from 354 entries (the installation's own figure; an illustration, not measured here) to the set this plan triages. The same installation's 2026-10-03 handoffs became plan 128 (its lessons a–e).

The handoff asks for a plan for the 2.0 line and treats the lessons as **INPUT, not decisions**: for each lesson, decide whether 2.0 already covers it (cite the mechanism), whether it belongs in a command / helper / agent brief / template / `FINDINGS.md`, or whether it is consumer-only and stays out. `## Disposition — all 54 lessons` records that call for every lesson; `## Phase 0 — ratification` proposes what to build for the gaps.

**Markers.** Every lesson carries a marker. `[ANY]` means every stack. A stack marker — `[NPM]`, `[TS]`, `[VITE]`, `[VITEST]`, `[VUE]`, `[GQL]`, `[DOCX]`, and `[BACKEND]` on one row (E1) — means that tooling only. The sender's guidance: `[ANY]` rows are candidates for framework mechanisms; stack-conditional rows are candidates for a consumer's own memory, NOT for commands. Two `[ANY]`-marked rows are stack-shaped in content (P8 typed-language-shaped, K10 framework-specific); the disposition table says so where it places them.

**The auto-memory block.** The data ends with a block titled "Auto-memory entries to copy" — six user-level entries of the sending consumer. It is context only, not a request. `## Disposition — all 54 lessons` records what it means for Forge, below the table and outside the 54.

This repo is public. **Public-repo rule: name no client, company, workspace, package, ticket or spec number and no path outside this repo** — in this plan and in every phase, commit, record and ledger line it drives. The installation is "one consumer installation (wrapper mode, running the 1.x command layout)"; the sender is "a sibling session".

---

## Overlap with plan 128 — what is NOT re-decided here

`128-AC-VERIFICATION-COMMAND-GATE-PLAN.md` (Phase 0 OPEN, nothing ratified on 2026-10-05) came from the same installation and the same sender. It already decides the items below; this plan cites them and re-decides none.

- **Lesson (a), baseline-measured grep gates** → 128 D3: a spec-time baseline on `add-ac`, with a hygiene refusal when the command already passes.
- **Lesson (b), a verify-time re-run after the LAST task** → 128 D4 (a verify-time verb, `check-ac-commands` per its OQ-1, at `/devforge:verify` 4.6) and 128 D2's path-scoping rule: a hygiene command is scoped to a path, never `.`, and when test files are excluded the AC's statement says so.
- **Lesson (c), evidence outside `/tmp`** → 128 D3, D5 and D7: the values live on the AC and in `verification.md`, and harness scripts are FEATURE-SCOPED under `specs/<feature>/` (`src/devforge/storage-rules.md:126` on 2026-10-05; 128 cites the same rule as `:125`).
- **Lesson (d), the tree hash in the report** → 128 D5 (`**Source tree**: <tree_sha> @ <head_sha>`).
- **Lesson (e), a negative control** → 128 D3's hygiene refusal.
- **128 D6 and D7 decline any plan-side or breakdown-side lane and any harness / baseline / verify directory convention; D7's counter-argument RECORDS the installation's measure-first wins without deciding them.** The new data's "Measure before planning, ladder with a predicted count per rung" (R6) is that same item. This plan does not re-open it; it cites 128 D6 and D7.
- **128 D8:** measured commands never enter `/devforge:implement`'s self-repair loop — an agent given "make N equal M" edits the measurement.
- **128 D9 (b) already routes the memory-consolidation gap to `FINDINGS.md`** — no size budget, no prune, and `/devforge:finalize` only READS and COMMITS `.devforge/memory.md` — as a new entry written in 128's Phase 4; nothing builds it. 128 D9 (a) declines a new memory-template SECTION.
- **The cost bound 128 F10 states, derived from stub plan 124's measurement** (`128-AC-VERIFICATION-COMMAND-GATE-PLAN.md:70`): any added lane must be mechanical, add no `AskUserQuestion` stop, and add at most one helper call per command. Plan 124 is a stub; the bound is 128's own. Each decision below states its cost against that bound.

---

## Verified structure (2026-10-05)

⚠ **Line digits drift — grep the quoted text, never the digits.** Every `file:line` below was read against this tree on 2026-10-05.

**F1 — The regression gate compares EXIT CODES, discards the output, and goes blind when the baseline is red.** `src/devforge/lib/_verify/_regression.py:3` *"Runs a baseline-diff regression check: compares the test suite exit code at"*; `:436` `baseline_status = "pass" if baseline_rc == 0 else "fail"`; `:446` `head_status = "pass" if head_rc == 0 else "fail"`; `:451`–`:454` `if baseline_status == "fail": return {"status": "baseline-failing", "regression": False, …`. Only the first configured test command runs (`:168` `first = (cmds[0] or "").strip()`; the docstring at `:60` names it `TEST_COMMANDS[0]`). `_run_test_cmd` (`:304`) returns `proc.returncode, _tail_text(combined)` (`:321`) — the LAST 50 lines only (`_TAIL_LINES = 50`, `:101`; `_TEST_TIMEOUT = 600`, `:107`); the baseline tail is bound to `_baseline_tail` (`:435`) and never used. The worktree: `tempfile.mkdtemp(prefix="forge-regression-")` (`:418`), `_add_worktree(source_root, worktree_dir, merge_base_sha)` (`:420`), and `_symlink_deps` (`:267`), which symlinks `_DEP_DIRS = ("node_modules", ".venv", "venv", "vendor")` (`:113`) as whole DIRECTORIES (*"top-level only, MVP scope"*, `:271`); the worktree is removed in a `finally` block (`:438`–`:442`). Consequences: one pre-existing failure or flake at the merge-base turns the gate off for the whole feature (status `baseline-failing`, never `regression`), and a flake at HEAD on a green baseline reads as a regression. The lesson's form — "a directory symlink lets TypeScript escape into the main tree" — names exactly what `_symlink_deps` does; D1 records it as a bound, not a build item.

**F2 — Nothing executes a falsification of new tests; the principle exists as prose.** `src/constitution.md:96` *"a repaired defect gets a test that fails without the repair"*; `:100` *"For every test there is a change to the code under test that makes it fail."*; `src/agents/qa-reviewer.md:63` *"there must be a change to the code under test that would make it fail"* — qa-reviewer is read-only (`:61`), so the rule is judged by reading; `qa-reviewer.md:27` flags three vacuous shapes (a value the test configured a mock to return, a literal compared with itself, no assertion); `src/agents/qa-engineer.md:36` *"Run the tests — verify they pass (or fail-first if pre-implementation)"*. A grep for `falsif|mutation|revert|red first|tautolog|cannot fail|git checkout .* --` over `src/agents`, `src/commands`, `_implement`, `_verify` and `_fix` finds no test-falsification step: its hits are other senses — runtime-debugger's "revert failed fixes", `/devforge:research`'s hypothesis falsifiers, spec-formalizer's and `/devforge:spec-check`'s formal falsification, and state / GraphQL "mutation" wording. No test-file pattern exists anywhere in config: `PACKAGE_STACKS` carries `{path, language, framework, build_tool, build_command, type_check_command, lint_command, test_command}` (`src/commands/configure/main.md:129`).

**F3 — ac-verifier runs BEFORE the mechanical gates, never sees their logs, has Bash, and contradicts itself on whether it runs the suite.** `src/commands/verify/main.md:243` *"`--iteration 0` is passed deliberately: it asks for ONE pass"* (PHASE 4.1, `implement_helper verify-touched`); `:212` *"it does NOT receive live test outcomes at dispatch time, because it is dispatched here in PHASE 3, before PHASE 4 runs the suite"*. `src/agents/ac-verifier.md:3` (description) *"…run the test suite under tests, or read code…"* versus `:38` *"you do NOT receive live test outcomes. The assembled test suite is a separate mechanical signal run by the orchestrator (not consumed by you)"* versus `:131` *"`tests` relies on the test-suite outcomes"*. No rule forbids the agent from running build / type-check / lint / test commands itself (a grep for `never run|do not run|type-check|lint|build command|test command` over the file returns nothing), and its `tools:` line includes Bash (`:4`).

**F4 — Vacuous / not-run results never block and mostly never reach `verification.md`.** `src/commands/verify/references/report-format.md:103` *"Every other status — `off` (gate disabled), `inconclusive` (…), `clean` (…), `baseline-failing` (…) — adds NO blocker and NO Reason line; it leaves the verdict unaffected and writes nothing to `verification.md`."* Zero dead-code rows yield `"status": "vacuous"` (`src/devforge/lib/_verify/_dead_code.py:193`–`:195`), and `compute_verdict` reacts to the dead-code dict only on `violation` (`_verify/_verdict.py:484`). e2e `off` is silent (`_verdict.py:521`), and a suite command that exits 0 is `e2e-clean` (`_verify/_e2e.py:321`–`:323`), so a suite with zero scenarios that exits 0 reads clean. `_verdict.py:146` `_PASSING_MECHANICAL = frozenset(["pass", "", None])` — "not run" counts as pass. `_implement/_cmds_verify.py:27` *""N/A" commands are silently skipped (not a failure)"*. A `pass` with an empty `test_commands_run` is caught by `/devforge:implement` (`src/commands/implement/main.md:184`: *"a `pass` with an empty `test_commands_run` means verification succeeded without a single test running. Capture it; PHASE 7's approve path reads it"*) but NOT by `/devforge:verify`. `verify/main.md:193`: an empty AC list *"is valid, not an error"*. `UNVERIFIED` ACs never block: only `FAIL` / `PARTIAL` count as AC failures (`_verdict.py:57`, `:149`–`:152`), and `UNVERIFIED` / `MANUAL` are excluded from the failure-rate denominator (`:156`–`:157`).

**F5 — `verify-touched` runs lint per PACKAGE on exit code and computes no warning delta; the task template says the linter passes "on changed files".** `_implement/_cmds_verify.py:99` example `"lint_command": "npx eslint src/"`; `:659` `if rc != 0:` … `:673` `break  # Stop at first failure; report it.`; the word "warn" does not occur in the module (case-insensitive grep). `src/devforge/lib/breakdown_helper.py:1007` `"Linter passes on changed files (see Development Commands section)"` and `src/devforge/storage-rules.md:241` `- [ ] Linter passes on changed files (see Development Commands section)`. Order: `:619` *"All commands to run: type-check, then lint, then build, then test."*, `all_cmds = verify_cmds + build_cmds + test_cmds` (`:624`) — type-check BEFORE build, touched packages only, no dependant-package awareness.

**F6 — The self-repair brief forbids nothing about generated/ignored artifacts or configuration, and the touched-file capture cannot see ignored-file edits.** `src/commands/implement/references/agent-brief.md:18` *"the original brief PLUS the helper's `failed_command` and `output`. … it must not expand scope beyond the failure"*. The bans present are forge artifacts in the source tree (`agent-brief.md:14`, `implement/main.md:154`) and "never weaken an assertion" (`constitution.md:96`). `_implement/_cmds_capture.py:6`–`:11`: the touched set is the union of `git diff --name-only <checkpoint-sha>` and the `??` lines of `git status --porcelain` — no `--ignored`, so an edit to a gitignored file (e.g. a package's `dist/*.d.ts`) is invisible to the touched set, the review panel and the WIP commit (inferred from git behaviour, not run). `FINDINGS.md` entry 11 (recorded 2026-10-05) covers the pre-existing-dirty-path arm of `capture-touched-files`, not the ignored-file arm. A broken command routes to `/devforge:configure` only through the `tooling_unavailable` status (`src/commands/fix/main.md:352`), which the helper raises on shell exit 127, "command not found", or "not recognized as an internal or external command" (`implement/main.md:188`).

**F7 — `/devforge:implement` has no stop-and-amend-spec path.** Its stops are the architect / missing-agent HALT (`implement/main.md:150`), the dependency `blocked` state (`:104`), and the gate-blocked path `["repair", "skip", "stop"]` (`:329`–`:336`). Deviations are recorded only via `mark-complete --notes` (`:282`). The only route to a spec-level change is `/devforge:verify` NEEDS WORK → *"a fresh `/devforge:specify` → `/devforge:plan` → `/devforge:breakdown` cycle for a spec-level change"* (`verify/main.md:183`).

**F8 — Wrapper isolation is an EXISTENCE check over a fixed list that lacks `.devforge` and treats a client's own `.claude/` or `CLAUDE.md` as pollution.** `_implement/_cmds_verify.py:187`–`:197` `ISOLATION_ARTIFACTS = (".claude", "specs", "docs/overview.md", "docs/architecture.md", "constitution.md", "CLAUDE.md", "bugs", "research", ".mcp.json")`; `_check_wrapper_isolation(source_root)` (`:514`) records an entry when `if candidate.exists():` (`:528`); it runs only when `workspace.is_wrapper` (`:601`), BEFORE the commands, and returns `{"status": "isolation_failure", "artifacts": [...]}` with exit 2 (`EXIT_FINDINGS`, `:604`–`:610`). `implement/main.md:187`: *"the agent polluted the **source** tree with forge artifacts … On `repair`, instruct the implementing agent to REMOVE the misplaced artifacts from the source tree"*; `:331`: the task *"never reaches the `approve` prompt"*. The lesson's installation legitimately carried `.claude/settings.local.json` inside the inner repo ("the inner repo's `.claude/settings.local.json` is the user's own"); under 2.0 that install is gate-blocked on EVERY task and told to delete the user's file. Because the check tests existence, not `git status`, EMPTY stray directories ARE caught — the lesson's "git status cannot see empty directories" does not apply to this detector. `verify-touched` takes `--files` and `--iteration` only (`implement/main.md:179`), no checkpoint sha. Tests pin `.claude` and `CLAUDE.md` as pollution: `tests/lib/_implement/test_cmds_verify.py` `test_claude_md_found` (`:1079`) and `test_dot_claude_dir_found` (`:1085`). `.devforge` and `tickets` are absent from the list; `tickets/` is created lazily by `/devforge:report-ticket` (`DEVELOPMENT-STATUS.md:72`, under `### Other`).

**F9 — The pre-commit hook is installed to a hard-coded path, is a silent no-op when the helper is not where it looks, and nothing checks it is active.** `src/commands/constitute/main.md:629`–`:630`, the two installed lines: `cp .devforge/templates/git-hooks/pre-commit-forcing-functions.sh .git/hooks/pre-commit` / `chmod +x .git/hooks/pre-commit` — no `core.hooksPath`, no wrapper branch (the only wrapper mentions in the file are `:15` and `:596`). `src/git-hooks/pre-commit-forcing-functions.sh:19` `ROOT="$(git rev-parse --show-toplevel …)"`, `:25` `HELPER="$ROOT/.devforge/lib/constitute_helper"`, `:32`–`:34` `if [ ! -x "$HELPER" ]; then exit 0`. In wrapper mode the install root's `.git/hooks` guards the WRAPPER repo, while code commits land in the nested source repo, whose own hooks run instead — so this hook never runs on them; copied into the source repo, it exits 0 silently because `.devforge/lib` is not under that toplevel. `scripts/post-update-checks.sh:83` `forge_check_precommit_hook` resolves the ACTIVE hook via `git -C "$target_dir" rev-parse --git-path hooks/pre-commit` (`:101`; comment `:98`, *"honors core.hooksPath"*), but `[ -f "$hook_path" ] || return 0` (`:110`) — a MISSING hook is silent; the function reports only drift from the shipped template. No command claims the hook ran: a grep for "hook" over `src/commands/finalize`, `src/commands/verify`, `src/commands/review` and `src/devforge/lib/_finalize` returns zero hits. Mitigation already present: the forcing-functions detectors also run at `/devforge:implement`'s per-task gate (`implement/main.md:331`, *"PHASE 6's forcing-functions gate"*; `constitute/main.md:274` says of `design_token_provenance` that it *"runs at the `/devforge:implement` per-task gate and the opt-in pre-commit hook"*).

**F10 — `/devforge:review` checks a finding's quote ANYWHERE in the file, never at the cited line; refuter quotes and partner citations are unchecked; the report format advertises a tag nothing produces.** `src/devforge/lib/_shared/_validate.py:210` `if line_no < 1 or line_no > line_count:` (range only); `:219` `if not normalised_evidence or normalised_evidence not in normalised_file:` (a substring of the WHOLE normalised file) — so a finding that cites `:490` for code at `:492` passes. `review/references/refutation-preamble.md:27`–`:28` *"The quote must be a literal substring of the actual file"*, but `_shared/_verify.py` `apply_verdicts` (`:564`) has no substring check (the word does not occur in the module). `review/references/emergent-issue-checklist.md:116`–`:118`: the partner file *"is named in `Why it's wrong:` by path and line, not quoted in `Evidence:`"*. A line-scoped precedent exists: `src/devforge/lib/_generate_docs/_validators_shared.py:101`–`:102` `"snippet-verbatim"` … *"snippet does not match {1}:{2}-{3}"* (it compares the cited line RANGE). `review/references/report-format.md:53` *"Finding tags: `[CROSS-AGENT]` (raised by ≥2 finders), `[CONSTITUTION-VIOLATION]`"* and `_review/_report.py:134` *"[CONTESTED] and [CROSS-AGENT] tags are preserved from the finding's tags list"* — but `compute_consensus` (`_shared/_consensus.py:114`) is called only from `_audit/_cli.py:676` / `:707` (`audit_helper compute-consensus`, `audit/main.md:354`); `/devforge:review`'s `### 2.6 — Combine validated findings` (`review/main.md:248`) joins arrays and never produces the tag. The consensus rule: `_consensus.py:22` *"Group key = (file_path, line_number, category)"*; `:31`–`:33` *"Corroboration is gated on ≥ 2 DISTINCT agent names … Tag [CROSS-AGENT] … Bump severity one level"*. `review/main.md:200` is the `validate-findings` call; `## PHASE 3 — Refutation (cross-examination)` (`:266`) runs on the *"deduped working list, AFTER validation and BEFORE the report"* (`:272`); `_audit/_merge.py:22` *"correlated re-generation is not independent corroboration"*.

**F11 — Refutation has no reachability criterion.** The review and audit refutation preambles — `src/commands/review/references/refutation-preamble.md` and `src/commands/audit/references/refutation-preamble.md`, identical except at `:3` and `:6`, where each names its own run — read at `:10` *"A finding earns "confirmed" ONLY when you can demonstrate the defect from the quoted code in front of you"*, and at `:47` the counter-quote is *"(the guard, the code path, the call site that makes the finding wrong)"*. A grep for `reach|entry point|dormant|instantiat|caller` over those preambles returns nothing, and `render_verify_brief` (`_shared/_verify.py:374`) adds no such criterion. Nearest analogs, outside refutation: `src/commands/specify/main.md:667` *"show that state REACHABLE: cite the construction site that produces it … traced through the codebase-memory-mcp chain"*; `src/agents/security-reviewer.md:73` *"Flag only exploitable vulnerabilities, not theoretical risks"*.

**F12 — Dead-code closure and anchors: bounds already stated; no import-graph closure, no byte delta.** `src/commands/plan/main.md:437` (architect sub-question 9): *"trace the code the decision touches (`trace_path` / `search_code` on the ACTUAL code, NOT from memory) and return one table row per killed path … the **anchor token** is a literal string lifted from the code whose ABSENCE in the post-change file proves the path was removed"*; `src/devforge/lib/_verify/_dead_code.py:57`–`:58` *"The declared file EXISTS and still contains ``anchor_token`` as a literal substring → "violation""*; `:80` *"This check confirms REMOVAL of the DECLARED kill-list only"*; `:88`–`:91` *"the presence check is a LITERAL SUBSTRING match anywhere in the file … It does not distinguish a genuine leftover … from the same token incidentally re-occurring elsewhere"*. `src/commands/breakdown/main.md:492` *"never line numbers. Line numbers shift as earlier tasks modify files."* (the same rule at `:710`); `plan/main.md:444` carries `/devforge:research` citations — *"do not re-derive it"*; `breakdown/main.md:166` names the optional advisory drift check `cbm_sync_helper check-spec <spec-path>`.

**F13 — Provenance and numbers.** `src/commands/research/main.md:860` *"Run `git log -S "<literal>" -- <file>` … The introducing commit is the OLDEST commit whose diff added the literal"*; `:872` *"Open the diff (`git show <sha>`) … the subject line is a filter, not the answer."* — this fires only for a hardcoded primitive literal (`:856` *"Array / object / regex / function literals are OUT OF SCOPE"*). `/devforge:fix` has no git-history step: a grep for `git log|git show|git blame` over `src/commands/fix` returns nothing. `src/commands/specify/main.md:1031` (IMPORTANT RULE 8) *"for every count, size, version number, or line number you write into the spec, verify by direct Bash enumeration before writing."*; `_specify/_cmds_phase4_verify.py:123`–`:125` *"Variance rule #6: digit-prefixed nouns consistent across spec. … Advisory / non-blocking — always exits 0."* (internal consistency only); `specify/main.md:208` *"A carried memory entry is an UNVERIFIED prior-session assertion"*. `specify/main.md:663` *"Each AC must be testable and unambiguous."* — nothing about values versus field presence.

**F14 — Docs staleness.** `src/devforge/lib/_generate_docs/_validators_file_doc.py:185` `_check_annotation_cite_resolves`, including `'hash_drift'` (`:194`, `:240`), plus `snippet-verbatim` (F10) — only for citations `/devforge:generate-docs` registers; `src/agents/tech-writer.md:233` *"No references to code that doesn't exist"* (instruction only); `src/commands/finalize/main.md:282`, the structural-drift reminder, is *"a soft pointer, NOT a gate"*. No phantom-name or prose-identifier check exists: a grep for `phantom|backtick|identifier.*resolv|stale` over `_generate_docs`, `_finalize`, `_summarize` and `tech-writer.md` hits only snippet-staleness messages, backtick rendering and state-file handling — none resolves a prose identifier.

**F15 — Memory.** The template `src/devforge/memory.md:1`–`:13` holds four headings with HTML comments (`## Architecture Decisions`, `## Known Pitfalls` — *"Populated during work as mistakes are discovered"*, `## What Worked`, `## What Failed`) and no entry-format rule. The only command that WRITES a lesson into it is `/devforge:verify` PHASE 7 (the others read or commit it) — `src/commands/verify/main.md` `## PHASE 7 — Memory update` (`:372`): `:378` *"an entry already covering this lesson makes an append a duplicate — sharpen or extend the existing wording instead of restating it"*; `:380` *"Keep it LIGHT: feature-level only, never a per-task re-log"*; `:384`–`:386` the three buckets, after `:382`'s *"there is no fourth bucket"*; `:390` *"insert the short dated entry immediately BEFORE the next `## ` heading"*. There is no size, entry-count, tag or spec-pointer rule, no "supersede when a fact changes" and no "never cite by position". The read side is bounded: `src/devforge/lib/_shared/memory.py:327` `DEFAULT_EXCERPT_LINES = 120`. The path is install-root relative: `:131`–`:132` *"a workspace_root (the install root -- .devforge/ always lives there, even in wrapper mode"*, `:147` `MEMORY_RELATIVE_PATH = ".devforge/memory.md"` — so the lesson's "two files named MEMORY.md" is N/A on 2.0. `_finalize/_preflight.py:214` `preflight_context` carries `memory_excerpt` (`:247`).

**F16 — Secrets.** "redact" has zero hits under `src/` (case-insensitive). No secret or credential scan exists in `_finalize`, `_verify`, `_report_bug` or `_design`, and none runs over `specs/<feature>/`. `src/agents/ac-verifier.md:68` *"call the endpoint … with proper headers (Content-Type, Authorization if needed)"*; `:71` *"Record `PASS` / `FAIL` / `PARTIAL` with the request/response summary as evidence"*. `/devforge:configure` reads the CONTENTS of `.env`, `.env.local` and `.env.development` into context: `_configure/_cmds_read.py:214` (inside `_CONFIG_FILE_BASENAMES`, `:207`), `_CONFIG_FILE_MAX_BYTES = 10 * 1024` (`:218`); `src/commands/configure/main.md:89` *"Each match carries its file content (capped at 10 KB"*; `:146` extracts `AC_RUNTIME_API_BASE` from `.env*` matches. The only secret rules target source code: `src/devforge/storage-rules.md:242` *"No new secrets or credentials in code"* and `src/agents/security-reviewer.md:29`. `_finalize/_preflight.py` holds `_git` (`:88`), `_count_wip_commits` (`:118`), `_ref_exists` (`:166`), `_autodetect_base` (`:173`) and `preflight_context` (`:214`).

**F17 — Browser / API verification mutates state by design, and "read-only" there means "do not edit source".** `src/agents/ac-verifier.md:125` *"**Never modify source code** — verification is read-only observation"*; `:60` *"establish required state through the app's own UI (`fill`, `click`) or inject it via `evaluate_script` (localStorage, cookies, fetch)"*; `:67` *"make prerequisite API calls via shell `curl` or `evaluate_script` fetch"*; `:70` *"for persistence, make a follow-up GET; for a state change, verify via another endpoint"*. `src/agents/design-auditor.md:34` navigates the binding's `route`; `:37` *"recommend a representative seed"*; `:49` *"Read-only — report findings, do not modify CSS or source."* `src/commands/verify/main.md:310` *"The suite owns the application lifecycle"*. `ac_runtime_url` / `ac_runtime_api_base` come from `.devforge/project-config.json` through `verify_helper read-ac-config` (`verify/main.md:193`, `:205`; `def cmd_read_ac_config(args):` at `src/devforge/lib/_verify/_cli.py:213`, registered at `:1161`, dispatched at `:1377`), and are set at `/devforge:configure` (`configure/main.md:145`, `:193`, `:237` `set-ac-runtime-url`). No rule names a disposable record, blocks mutations, or marks a mutating flow manual.

**F18 — Wrapper mechanics on 2.0.** The diff basis is the merge-base, not the working tree: `src/commands/review/main.md:144` and `src/commands/verify/main.md:147` — *"`resolve-feature-scope` runs `git diff --name-only $(git merge-base <base> HEAD)..HEAD` with `cwd = source-root`"*, the base auto-detecting `origin/HEAD → main → develop → master` (`review/main.md:144`). `/devforge:implement` diffs against the recorded checkpoint (`_cmds_capture.py:6`–`:8`). WIP staging is per path: `_implement/_cmds_commit.py:56`–`:59` *"Stage paths individually (`git add -- <path>`). NEVER `git add -A`. … WRAPPER: stage ONLY source touched_files in the SOURCE repo"*. `.devforge/wip.md` is EPHEMERAL since plan 111 (`3fa3b10`; `src/files/devforge.gitignore:3`). `CLAUDE.md` is substituted in place and three-way merged on update (`src/commands/configure/main.md:17` *"`CLAUDE.md` — substituted in place; no `{{KEY}}` markers remain."*; `src/manifest.json:29`, three-way merge), so the 1.x premise "project-config regenerates CLAUDE.md" does not hold — and the inverse bound holds: a later `configure.yaml` change does not reach an already-substituted `CLAUDE.md`. **Nothing writes the inner-repo ignore line.** `src/files/devforge.gitignore:1`–`:21` holds `.devforge/…` lines only; `install.sh` merges that template into the target `.gitignore` (`:339`–`:345`), and `update.sh` sources `.gitignore` from the same template (`:554`–`:556`); `src/devforge/lib/init_helper.py` has no `gitignore` / `info/exclude` hit; `src/commands/init-forge/main.md:78` names `.gitignore` only in its emptiness-judgement ignore list. **`DEVELOPMENT-STATUS.md:83` claims the opposite:** *"`/devforge:init-forge` detects nested git repos and confirms adding the inner folder to `.gitignore` during STEP 0"* — `init-forge/main.md` has no STEP 0, and its wrapper substep (`### 1.2: Resolve Wrapper Source Root`, `:45`–`:72`, `find-nested-git`) asks which folder is the source root and writes no ignore line. `115-WRAPPER-INNER-REPO-CBM-VISIBILITY-PLAN.md` (a stub) owns the adjacent problem — an ignore entry blinds CBM; `.cbmignore` negation — and says *"Nothing in install / init-forge detects or guides this"* (`:8`). The anchoring trap: an unanchored `<inner>/` also ignores `docs/<inner>/`, and `/devforge:finalize` runs `git add docs/ && git commit …` (`src/commands/finalize/main.md:154`).

**F19 — `update.sh` overwrites emitted commands by documented policy and preserves state files.** `update.sh:1093`–`:1096` *"Overwrite semantics here are deliberate: commands are framework-owned (matches templateOwned policy). User-modified target commands are NOT preserved across updates. Project customizations live in CLAUDE.md and the agents — those still three-way merge upstream"*; `scripts/emitters/claude.py:82` is a plain `write_text`; `src/commands/configure/main.md:453` *"that re-emit overwrites every command file wholesale"*. Preserved: `install.sh:309` `_PRESERVE="memory.md project-config.json"`; `src/manifest.json:36`–`:47` `projectOwned` lists `constitution.md`, `.devforge/project-config.json` and `.devforge/memory.md` (`src/devforge/storage-rules.md:124`: the list *"DOCUMENTS, it does not ENFORCE"*). `configure.yaml` is never shipped (`install.sh:260`, the stray-user-state guard), and of the two scripts only `update.sh` reads it (`:325`–`:331`). The data's auto-memory entry "a 1.x `update.sh` clobbers local `specify.md`/`plan.md` edits" holds on 2.0 too, by policy.

**F20 — Breakdown / test-strategy prose.** Ordering: `src/commands/breakdown/main.md:262` *"types before use, data before domain, core before presentation, independent before dependent, riskiest first"*; `:272` *"One task = one logical change** that can be verified independently."*; no "green between tasks" rule (a grep for `green between|stays green|keep.*green` returns nothing); `:457` names one case where the type checker suffices (*"the surface is a pure rename the type checker covers end to end"*, restructuring tasks). Test priority: `src/agents/qa-engineer.md:45` *"Prioritize what to cover: business logic > error handling > edge cases > rendering"* (the same order at `qa-reviewer.md:26`); the property lane targets *"deterministic, no-I/O construction (filters, queries, mappers, formatters)"* (`breakdown/main.md:405`); `src/agents/code-reviewer.md:38` names early-return guards only for change-induced dead code. `/devforge:fix`: the scope rule `src/commands/fix/main.md:332` *"Remediate ONLY the cited defect(s)…"*; qa-reviewer sits in the fix review panel (`:358`); no rule says when a fix needs a test.

**F21 — No PostToolUse type-check hook ships.** `src/settings.template.json:46`–`:55`: the `PostToolUse` array carries only `cbm-mcp-marker`. `src/hooks/` holds `bash-ban-raw-tools`, `cbm-code-discovery-gate`, `cbm-mcp-marker`, `cbm-session-reminder` and `cbm-sync-session-start`.

**F22 — Ledger shapes.** `FINDINGS.md` has 12 numbered entries (`## 12.` is the last). Entries carry *"NO `<NN>-*-PLAN.md` FILE EXISTS for this; do not grep for one"*, an **Evidence class** sentence, and AMENDED lines when later plans touch them — entry 10 shows the shape. `CHANGELOG.md` `## [Unreleased]` (`:8`) carries `### Changed` (`:10`) and `### Fixed` (`:18`) on 2026-10-05 — re-verify live, and never edit a released block. `PLAN-STATUS-ARCHIVE.md` lists plans up to 125; plans 126–130 are not listed. Registry pins: `tests/lib/_verify/test_preflight.py:728` asserts 16 verify registry entries (128 adds one); `tests/lib/_finalize/test_preflight.py:1161` asserts 5 finalize entries; `/devforge:review`'s registry has no `len()` pin under `tests/lib/_review/`.

---

## Disposition — all 54 lessons

The 54 rows follow the data's own grouping: Read first (R1–R7), Known Pitfalls on any stack (P1–P14), Known Pitfalls stack-conditional (S1–S15), What Worked (K1–K10), What Failed (W1–W4), External API quirks (E1–E2), Performance notes (N1–N2). Lesson wording is generic: no row names a client, company, workspace, ticket or spec number, or one of the installation's own packages; rows do name public tools and libraries (`rtk`, `sed`, `vitest`, `vite-plugin-dts`, `docx`), which are not installation identifiers. **2.0 state** is one of COVERED, COVERED-WITH-BOUND, COVERED-DECLINED, PARTIAL, PARTIAL-WITH-BOUND, ABSENT and OUT; a part of a row that does not apply to 2.0 is marked N/A inside the row. A **131-Dn** disposition is a proposal in `## Phase 0 — ratification`, not a ratified decision.

| # | Lesson (generic wording) | Marker | 2.0 state | Mechanism / F-ref | Disposition |
|---|---|---|---|---|---|
| R1 | A user-level shell hook (`rtk`, a public tool, not an installation identifier) rewrites command output | `[ANY]` TOOLING | OUT | The framework owns no shell hooks; F21 lists the only shipped hooks | Stays in the consumer's memory (D18) |
| R2 | macOS BSD `sed` / `comm` / `ls` and bracket-class differences | `[ANY]` TOOLING | OUT | Platform notes | Consumer memory (D18) |
| R3 | Memory grows append-only; an entry format (a two-line tagged, dated entry plus a pointer; edit in place; never cite by position); two files named `MEMORY.md` | `[ANY]` MEMORY | PARTIAL | F15 | Consolidation / size → 128 D9 (b) `FINDINGS.md` entry, not re-opened; entry format, supersede by delete-and-re-insert (newest last) and no positional citation → **131-D14**; "two `MEMORY.md`" → N/A (`.devforge/memory.md`, install-root relative) |
| R4 | Grep ACs measured at baseline, scoped, `--exclude-dir=test`, absence stated as "unchanged from baseline" | `[ANY]` VERIFY | COVERED | 128 D2 / D3 / D4 | Cite 128; no 131 decision |
| R5 | Plausibility is not evidence (equivalence claims, zero-hit citations, mis-cited lines and counts; verify at source when agents disagree; word-bounded counts) | `[ANY]` PROCESS | PARTIAL | F10, F11 | Line-scoped quote check → **131-D5 (a)**; count / equivalence grounding in refutation → **131-D6** |
| R6 | Measure before planning; a ladder with predicted counts; pin bytes | `[ANY]` PROCESS | COVERED-DECLINED | 128 D6 (no plan-side lane) and D7 (its counter-argument records it) | No re-open |
| R7 | Gate a suite on a NAME-level failure multiset, not the exit code; capture before the first edit | `[ANY]` TESTS | ABSENT | F1 | **131-D1** |
| P1 | Re-read a PASS against the AC's literal words; re-run grep ACs at verify; cascade a late fix into the docs | `[ANY]` | COVERED | 128 D4 (verify-time run); `parse_acs` `text` is the EARS sentence (128 F3); the docs cascade is `/devforge:finalize`'s tech-writer | No change |
| P2 | Wrapper mechanics: a gitignored WIP marker → stage the real files; diff ACs compare base..HEAD; project-config regenerates CLAUDE.md; `.gitignore` must anchor `/<inner>/` | `[ANY]` | PARTIAL | F18 | Per-path staging and the merge-base diff COVERED; CLAUDE.md regeneration N/A on 2.0 (the inverse bound is recorded in F18); ignore-line anchoring and the stale `DEVELOPMENT-STATUS.md:83` claim → **131-D15** |
| P3 | Stray forge directories inside the inner repo go unnoticed; the inner repo's `.claude/settings.local.json` is the user's own | `[ANY]` | PARTIAL | F8 | The existence check catches empty directories; `.devforge` / `tickets` are missing from the list; `.claude` / `CLAUDE.md` are a false positive → **131-D3** |
| P4 | A tracked hook is not an active hook (`core.hooksPath`, `.git/hooks/<name>`, `prepare`); a finalize recorded that a hook "genuinely ran" | `[ANY]` | ABSENT | F9 | **131-D4** |
| P5 | `file:line` citations shift; baseline anchors; verify with `sed -n` on the final tree; docs lag code | `[ANY]` | COVERED-WITH-BOUND | F12: breakdown bans line numbers in contracts; the advisory `check-spec` drift check; `/devforge:plan` reuses research citations by design (cost) | No change |
| P6 | Evidence inside `specs/<feature>/`, never `/tmp`; the harness refuses subagent report files, so the orchestrator writes them; gate scripts exit 2 on empty input; enumerate from manifests | `[ANY]` | PARTIAL | F4 | Location → 128 D7 (feature-scoped); orchestrator-writes is today's `$WORKDIR` pattern (finder temp files degrade to `missing`); vacuous / empty gate results → **131-D7**; manifests → OUT (stack) |
| P7 | A negative control; `LC_ALL=C`; diagnostic identity as a multiset; strip ANSI | `[ANY]` | OUT (negative control COVERED) | 128 D3 | Negative control → 128 D3; the rest is stack reference → consumer memory (D18) |
| P8 | Compiler masking (the first failing argument; a set-diff, not a raw count) | `[ANY]`-marked, typed-language-shaped | OUT | Stack reference | Consumer memory (D18) |
| P9 | Reachability triage (trace UP to a live instantiation site; dormant sites); assert VALUES in data-shape ACs | `[ANY]` | ABSENT | F11, F13 | Refutation reachability → **131-D6**; a `/devforge:specify` sentence (values, not presence) → **131-D11** |
| P10 | Deletion closures on the import graph; barrels shift anchors; a bundle byte delta | `[ANY]` | PARTIAL-WITH-BOUND | F12 | One sentence in sub-question 9 → **131-D11**; the byte delta → OUT (bundler-specific) |
| P11 | A captured dev-server module carries the environment (secrets); redact before committing evidence | `[ANY]` | ABSENT | F16 | **131-D9** |
| P12 | Lint ACs as "0 errors and no new warnings in changed files"; cached root scripts prove nothing; grep a package's scripts before writing a verification AC | `[ANY]` | COVERED-WITH-BOUND | F5 | Package-level lint implies the template's "on changed files" → **131-D12** (decline); the bound is the per-file warning evidence the report never shows; a non-existent script in an AC command → 128 D3 refuses it (exit 127); warning deltas → declined (`## Non-goals`) |
| P13 | `git log -S` the guard before repairing; verify a precedent commit by its DIFF | `[ANY]` | PARTIAL | F13 | A `/devforge:fix` sentence → **131-D11** |
| P14 | Re-measure; never cite a recorded number | `[ANY]` | COVERED-WITH-BOUND | F13: `/devforge:specify` IMPORTANT RULE 8; `/devforge:plan` carries research citations by design | No change |
| S1 | Forced turbo runs; `env -u` against agent-detecting writes; CI-only build scripts | `[NPM]` | OUT | — | Consumer memory (D18) |
| S2 | An install does not build; a stale `dist` defeats a per-edit type-check; re-probe the environment | `[NPM]` | PARTIAL | F5 (type-check before build in `verify-touched`); F21 (no PostToolUse hook ships, so that premise is N/A) | The generic mechanism → **131-D13** |
| S3 | A branch switch leaves `node_modules` stale; robust command forms | `[NPM]` | OUT | Adjacent: plan 116 (stub) | Consumer memory (D18) |
| S4 | `overrides` propagation; turbo `globalDependencies` | `[NPM]` | OUT | — | Consumer memory (D18) |
| S5 | Lockfile regeneration traps | `[NPM]` | OUT | — | Consumer memory (D18) |
| S6 | Registry auth via a project `.npmrc` | `[NPM]` | OUT | — | Consumer memory (D18) |
| S7 | TypeScript emit damage (TS4019 / TS4033 silent) | `[TS]` | OUT | — | Consumer memory (D18) |
| S8 | Four root causes behind declaration diagnostics | `[TS]` `[GQL]` | OUT | — | Consumer memory (D18) |
| S9 | `vite-plugin-dts` behaviours | `[VITE]` | OUT | — | Consumer memory (D18) |
| S10 | Interface / implementation drift; query-shape changes invisible to the compiler; nominal classes | `[TS]` | OUT | — | Consumer memory (D18) |
| S11 | vitest's `Type Errors` summary versus its exit code; `typecheck.*` config | `[VITEST]` | OUT | — | Consumer memory (D18) |
| S12 | Vue test-harness stubs | `[VUE]` | OUT | — | Consumer memory (D18) |
| S13 | `DeepReadonly` store state | `[VUE]` | OUT | — | Consumer memory (D18) |
| S14 | Codegen discipline | `[GQL]` | OUT | — | Consumer memory (D18) |
| S15 | Modal-stack dedup | `[VUE]` | OUT | — | Consumer memory (D18) |
| K1 | Run heavy gates once in the orchestrator; hand the logs to ac-verifier with "do not rebuild"; a tree hash; a `verify/run-gates.sh` | `[ANY]` | PARTIAL | F3 | Gates already run once (4.1); tree hash → 128 D5; a `verify/run-gates.sh` would live in a verify directory, and 128 D6 and D7 decline any plan-side or breakdown-side lane and any harness / baseline / verify directory convention (D7's counter-argument RECORDS the installation's measure-first wins without deciding them); the ac-verifier contradiction and the missing "do not re-run" rule → **131-D10** |
| K2 | A falsification protocol (commit; revert one source file at a time; run all new specs; pair a negative with a positive; a second fixture value) | `[ANY]` | ABSENT | F2 | **131-D2** (mechanical: new tests at the merge-base) + **131-D11** (qa-engineer / qa-reviewer sentences) |
| K3 | Whether a fix needs a test hinges on the diagnostic family; a test that cannot fail is worse than none | `[ANY]` | ABSENT | F20 | **131-D11** (`/devforge:fix`) |
| K4 | Coverage skews to pure code; integration layers and the fall-through branch of a new guard; extract loops; the `it.each` trap | `[ANY]` | ABSENT | F20 | **131-D11** (qa-engineer + breakdown) |
| K5 | When a measured ladder breaks, stop and amend the spec; order tasks so the type checker never goes red between them; repair before the migration that removes the old gate | `[ANY]` | ABSENT | F20 (ordering), F7 (stop-and-amend) | Ordering → **131-D11** (breakdown); stop-and-amend → **131-D16 (c)** `FINDINGS.md` entry (declined to build) |
| K6 | Two review agents, one pointed question; spot-check every citation before `review.md` | `[ANY]` | ABSENT | F10 (absent in `/devforge:review`) | **131-D5 (b)** |
| K7 | A throwaway `git worktree` of the old commit, deps symlinked entry by entry, plus a negative control | `[ANY]` | PARTIAL | F1: the regression gate's worktree exists, with DIRECTORY symlinks | Bound recorded in **131-D1**; no change |
| K8 | Browser techniques (hard reload, a declared event via `app._instance.subTree`, a fetch patch, a fallback into a browser-only AC) | `[ANY]` | OUT | Technique notes | Consumer memory (D18); the SAFETY half is W2 |
| K9 | A docs-staleness pass measured per statement; phantom-name harness limits | `[ANY]` | PARTIAL | F14 | **131-D16 (b)** `FINDINGS.md` entry |
| K10 | A memoized mapper computed; precomputed flags; additive optional filter params | `[ANY]`-marked, framework-specific | OUT | — | Consumer memory (D18) |
| W1 | Assuming a predecessor spec branch is merged; workspace-wide "zero matches" ACs | `[ANY]` | COVERED | 128 D2 (scope to the current feature's identifiers and a path) | No change |
| W2 | Read-only browser verification is not read-only on real data (a route mutated on load; a print route saved a file); block mutations, mark MANUAL, or name a disposable record | `[ANY]` | ABSENT | F17 | **131-D8** |
| W3 | Patching a package's gitignored `dist/*.d.ts` by hand; rewriting documented commands to match a stale tree | `[ANY]` | ABSENT | F6 | **131-D11** (self-repair brief constraints) + **131-D16 (a)** (amend `FINDINGS.md` entry 11: ignored-file blindness) |
| W4 | Targeted lockfile edits versus regeneration | `[NPM]` | OUT | — | Consumer memory (D18) |
| E1 | Client-side filters are UX, not authorization; a cache keyed on arguments | `[BACKEND]` | OUT | — | Consumer memory (D18) |
| E2 | `docx` library pitfalls | `[DOCX]` | OUT | — | Consumer memory (D18) |
| N1 | Vite chunk-table parsing (thousands separators) | `[VITE]` | OUT | — | Consumer memory (D18) |
| N2 | Shared externals across workspace vite configs | `[NPM]` | OUT | — | Consumer memory (D18) |

**Tally, counted from this table.** 54 rows. Each row is counted once, by its **2.0 state** column, except K9, whose only disposition is a `FINDINGS.md` entry:

- **COVERED** (incl. -WITH-BOUND / -DECLINED) — **7**: R4, R6, P1, P5, P12, P14, W1. P12's disposition is D12's decline.
- **PARTIAL → a 131 decision** (incl. -WITH-BOUND) — **10**: R3, R5, P2, P3, P6, P10, P13, S2, K1, K7.
- **ABSENT → a 131 decision** — **11**: R7, P4, P9, P11, K2, K3, K4, K5, K6, W2, W3.
- **→ `FINDINGS.md` only** — **1**: K9. K5 and W3 also carry a `FINDINGS.md` arm (D16 (c) and (a)) and are counted under ABSENT.
- **OUT** — **25**: R1, R2, P7, P8, S1, S3–S15, K8, K10, W4, E1, E2, N1, N2. P7's negative-control clause is COVERED by 128 D3; the row is counted here once.

7 + 10 + 11 + 1 + 25 = 54.

**The auto-memory block (six entries, context only — not counted in the 54).** Five entries — `language-ukrainian-chat-english-artifacts`, `lockfile-regeneration-is-default`, `grep-acs-match-their-own-fix`, `local-git-objects-not-a-risk`, `forge-repo-public-no-client-identifiers` — are user-level preferences of the sending consumer; nothing in them is for Forge. The sixth, `forge-active-line-is-2-0` (*"a 1.x `update.sh` clobbers local `specify.md`/`plan.md` edits; never run it on an installation with local command edits"*), holds on 2.0 too, by documented policy (F19). This plan records it and changes nothing (D18, `## Non-goals`).

---

## Phase 0 — ratification

Nothing below is ratified. Each item states the question, its proposal, a recommendation, what it costs, and the strongest counter-argument, **recorded honestly rather than answered away**. Where a proposal has a weakness that is not its strongest counter-argument, it is recorded as a **Bound, recorded:** line. Every cost is weighed against the bound 128 F10 states, derived from stub plan 124's measurement: mechanical, no added `AskUserQuestion` stop, at most one added helper call per command.

### D1 — Regression gate: a name-level failure multiset (R7, K7; F1)

**Proposal:** `_regression.py` keeps the full combined output of both runs, not the 50-line tail, and extracts failing-test identifiers from it with a fixed per-runner extraction table. The runner is detected from `test_command`'s first token(s): `pytest` (`FAILED <nodeid>` / `ERROR <nodeid>` lines), `vitest` / `jest` (`✕` / `×` lines and `FAIL <file>` lines), `go test` (`--- FAIL: <Name>`), `cargo test` (`test <name> ... FAILED`), `rspec` (`rspec ./<path>:<line>`). The two runs compare as MULTISETS (`collections.Counter`): `new_failures = head − baseline` — the names failing at HEAD that did not fail at the merge-base, with multiplicity.
- Status `regression` when `new_failures` is non-empty, EVEN WHEN the baseline is red — this removes the `baseline-failing` blind spot.
- Status `baseline-failing` only when the baseline is red and `new_failures` is empty; `clean` when both runs are green.
- The JSON gains `baseline_failures`, `head_failures`, `new_failures` and `extraction` (`<runner>` or `none`).
- When the runner is unknown, or extraction yields zero names on a non-zero exit, the gate falls back to today's exit-code semantics and records `extraction: none` with a note — never silently.
- A baseline or HEAD run that does not run at all — exit 126 or 127, a timeout, or an exception from `_run_test_cmd`'s three arms (`_regression.py:322`–`:327`), which Phase 1 stops collapsing into `(1, …)` — yields the gate's existing `inconclusive` status with the arm named in its `note`, as `_e2e.py` already does for a timeout (`:301`–`:305`; its docstring, `:93`–`:95`); today `:436` and `:446` read every non-zero code as `fail`, so a not-run baseline reports `baseline-failing` and a not-run HEAD run on a green baseline reports `regression`.

**Alternative considered:** a per-package `test_failures_command` config key (a JSON reporter). It is a `/devforge:configure` question — a stop, against the bound 128 F10 states, derived from stub plan 124's measurement — and a per-stack burden. Declined.
**Bounds, recorded.** **(1)** Output parsing is runner-specific, and custom reporters defeat it; the fallback is loud, not silent. **(2)** A flake that fails only at HEAD still reads as a regression. The lesson's "capture before the first edit" has no analogue here: the merge-base run IS the capture. **(3)** Duplicate test titles are counted with multiplicity — the lesson's `sort -u` undercount — which is why the comparison is a Counter, not a set. **(4)** `_symlink_deps` links `node_modules` and its siblings as whole directories; the lesson's "entry by entry" form (K7) is not built here. **(5)** Full output capture can be large; it is capped at a byte budget (e.g. 2 MB), with the cap declared in the note.
**RECOMMEND the extraction table** with the loud fallback. **Cost:** one module extension (the extraction table and the Counter diff), the JSON fields, prose in `report-format.md` and `verify/main.md` 4.3, and tests whose fixtures are real runner output samples committed under `tests/lib/fixtures/`.
**Counter-argument, recorded:** **a per-runner table is exactly the stack-specific knowledge the sender says belongs in consumer memory, and it will be wrong for the next runner.** The honest minimum is the fallback note plus the recorded bound.

### D2 — New tests at the merge-base: a falsification check inside the regression gate (K2; F1, F2)

**Proposal:** after the baseline run, in the SAME worktree, the gate identifies the feature's NEW test files — paths with status `A` in `git diff --name-status <merge-base>..HEAD` that match a fixed test-file pattern set (`*test*`, `*spec*`, `tests/`, `__tests__/`, `test_*.py`, `*_test.go`, `*_spec.rb`). It copies them, and only them, from HEAD into the worktree and runs `test_command` ONCE PER new test file, with that one path appended as a positional argument — one scoped run per file, not one combined run — so each file gets its own `passes_without_change` verdict. The loop runs EVERY new test file — it never stops at the first failure or rejection — and the rows are independent. The per-file verdict is a JSON key, `new_tests`: an array of `{file, exit, passes_without_change, output_tail}` rows, one per new test file; `output_tail` is the LAST 200 characters of that invocation's combined output, so a reader can tell an assertion failure, a collection failure and a rejected file argument apart. A runner prints its summary last — pytest's `Interrupted: N error(s) during collection` or `N failed` — but `_run_test_cmd` builds the combined output as stdout followed by stderr (`_regression.py:320`), so stderr text, when present, ends the tail instead. `output_tail` is taken from D1's full-output capture, which Phase 1 builds first; today `_run_test_cmd` (`_regression.py:304`) returns only the last 50 lines (`_TAIL_LINES = 50`, `:101`). Beside it the JSON carries `combined` (bool), `new_test_files` (the count of new test files) and `falsification`, one of `ran` (every invocation ran to an exit code, per-file or combined), `not_run` (at least one invocation could not run at all: exit 126 or 127, a timeout or any other exception raised by the run (`OSError` at `:324` or the catch-all `Exception` at `:326`, both of which return `1` today, so they must be caught as exceptions) — the `not_run` bullet below) and `n/a` (`new_test_files` is 0). The names avoid the regression gate's own `status: "inconclusive"` (`_regression.py:30`, `:352`), which `falsification` sits beside in the same JSON. A row whose run exits 0 at the merge-base carries `passes_without_change: true`; a row whose run exits non-zero with any code but 126 or 127 carries `passes_without_change: false` — "the test cannot pass at the merge-base" — whether the cause is an assertion, a collection failure or a runner that rejected the file argument (Bound 5). A row whose invocation could not run carries `passes_without_change: null`, with `exit` 127 for a missing command, `exit` 126 for a command found but not executable, and `exit: null` for a timeout or any other exception raised by the run, which end with no exit code. Under `not_run`, the rows that did run keep their values; under `n/a`, `new_tests` is `[]`. `compute-verdict` adds ONE reason line for the `true` rows, never a blocker: *"N new test file(s) pass at the merge-base without the change: …"*. In per-file runs, the reason line renders only for rows with `passes_without_change: true`; under `combined: true` every row carries `null`, and the reason line renders once, when the combined run exits 0 (the cap bullet below).
- **Cap: 10 new test files per feature.** Above the cap, the gate makes ONE combined run with every new test file appended; its exit code is a SET-level result, recorded as `combined: true`; every `new_tests` row then carries that run's `exit` and `output_tail` and `passes_without_change: null`, because no per-file verdict exists; and the reason line says the result covers the set, not each file, and renders only when that combined run exits 0.
- **`not_run` is never keyed on a runner's exit code.** It is recorded only when an invocation cannot run at all: exit 126 or 127 (the shell's "found but not executable" and "command not found" — `_run_test_cmd` runs with `shell=True`, `_regression.py:314`), a `subprocess.TimeoutExpired`, or any other exception raised by the run (`OSError` at `:324` or the catch-all `Exception` at `:326`, both of which return `1` today, so they must be caught as exceptions). The last two are recognised by the exception, never by the code: `_run_test_cmd` returns `1` for a timeout today (`:322`–`:323`) — the code pytest documents for failing tests — and `1` for an `OSError` or any other exception (`:324`–`:327`). ANY other non-zero exit is recorded as `passes_without_change: false`, whether the cause is an assertion, a collection failure or a runner that rejected the file argument (Bound 5). `falsification` is `not_run` when ANY invocation could not run; the rows that did run keep their values.
- A new test that fails at the merge-base because it imports a module the change adds is the CORRECT signal — it cannot pass without the change — and needs no special case.

**Alternative considered:** the lesson's full protocol — revert one SOURCE file at a time and re-run all new specs. That is N source files × one run each inside `/devforge:verify`; the cost grows with the diff, and the orchestrator must restore files from a manifest. Declined for cost; the merge-base check is one scoped run per new test file, at most 10 runs (Bound 4).
**Bounds, recorded.** **(1)** A characterization test of EXISTING behaviour legitimately passes at the merge-base — hence advisory. **(2)** A MODIFIED test file (status `M`) is not checked; only new files are. **(3)** The test-file patterns are a convention, not config: a project with unconventional names gets `0 new test files` and no reason line, recorded in the JSON as `new_test_files: 0`. **(4)** The cap of 10 is a cost bound, not a correctness one: above it, a combined run that exits 0 says the SET passes without the change, and a combined run that fails does not say which file would pass alone. **(5)** A runner that rejects the file argument reads as `false` for the wrong reason, and one that IGNORES it (a wrapper script or `make test` that runs the whole suite) or filters on it and matches nothing may exit 0, so the row reads `true` for the wrong reason and produces a spurious reason line; `output_tail` is the only tell in both directions. pytest reports a collection error as exit 2 "Interrupted" (its documented exit codes: 1 tests failed, 2 interrupted, 4 usage error), so an exit-code rule would have misread the CORRECT signal — a new test importing a module the change adds — as `not_run`.
**RECOMMEND as proposed.** **Cost:** one scoped test run per new test file — at most 10 per `/devforge:verify`, or one combined run above the cap; the pattern set; the JSON fields; one reason line; prose in 4.3 and `report-format.md`. **Coordination:** D2 reuses the regression-gate worktree that 128 D5's counter-argument leaves unreused (`128-AC-VERIFICATION-COMMAND-GATE-PLAN.md:128`); it does NOT re-measure AC commands at the merge-base — that lane stays open.
**Counter-argument, recorded:** **a reason line that never blocks is a signal the orchestrator may narrate and move past.** The lesson's installation found the protocol valuable because it was BLOCKING in practice ("redo after any later edit to a test").

### D3 — Wrapper isolation: what the client owns is not pollution; add `.devforge` and `tickets` (P3; F8)

**Proposal — the untracked-content rule:** `_check_wrapper_isolation(source_root)` keeps its signature. Before clauses (i) and (ii) below, `git -C <source_root> rev-parse --show-toplevel` must resolve to `<source_root>` itself (both paths resolved before comparing); otherwise — `<source_root>` is not a git repository, or it is a plain directory inside the wrapper repository, where `ls-files` would answer for the WRAPPER repository's index — today's existence check runs unchanged. When it does resolve, the rule flags an `ISOLATION_ARTIFACTS` entry ONLY when it exists AND either **(i)** it is EMPTY — a directory holding no regular file at any depth, so an entry holding only empty subdirectories is EMPTY and is pollution — or **(ii)** `git -C <source_root> ls-files --others --exclude-standard -- <path>` lists at least one file — that is, the path holds content that is untracked AND not ignored. A path whose content is all tracked, or all ignored, is the client's own. `.devforge` and `tickets` join the tuple. No flag is added: `verify-touched` keeps `--files` and `--iteration`, and the rule consumes no checkpoint sha. The `isolation_failure` remedy text exists at two sites — `implement/main.md:187` and `src/commands/fix/main.md:351`, each telling the agent to REMOVE the misplaced artifacts — and both name the rule: paths whose content the client repo tracks or ignores are the client's own.

Worked cases, one sentence each:
- A client `.claude/` with a tracked `settings.json` and nothing untracked is not pollution: its content is all tracked.
- A client `.claude/` holding only an ignored `settings.local.json` is not pollution: its content is all ignored.
- An agent-written `.claude/commands/devforge/` inside either of those `.claude/` directories is pollution: its files are untracked, and no ignore line covers them (Bound 4 names the exception).
- An empty stray `specs/`, or one holding only empty subdirectories, is pollution, by clause (i).
- A hand-made, unignored `.claude/settings.local.json` is pollution — Bound 2 stands.

**Alternative (a) considered:** a content-keyed carve-out — `.claude` flagged only when it holds `commands/devforge/` or a forge agent, `CLAUDE.md` only when it carries the emitted template's wrapper-mode heading. It is stateless, but it cannot help `specs/` or `docs/overview.md`, both plausible client names.
**Alternative (b) considered:** a snapshot — record each artifact's pre-task existence in `.devforge/wip.md` and compare. It adds a field to the marker plan 111 just reshaped (`3fa3b10`) and a second writer of that file.
**Bounds, recorded.** **(1)** An UNTRACKED, UNIGNORED client file that existed before the task is still flagged — the same bound `FINDINGS.md` entry 11 records for the touched set; it is also this decision's counter-argument, below. **(2)** `.claude/settings.local.json` is ignored only when Claude Code created it or the user added the line (`87-ARTIFACT-LANGUAGE-GUARD-PLAN.md` fact 3); a hand-made, unignored one still trips the check. **(3)** `tests/lib/_implement/test_cmds_verify.py`'s `test_dot_claude_dir_found` (an EMPTY `.claude` directory) and `test_claude_md_found` (an untracked, unignored `CLAUDE.md`) KEEP their meaning under this rule — both remain pollution. Their fixture is a plain `tempfile.mkdtemp()` directory, not a git repository, so after the change they exercise the fallback existence check. What changes is that the tracked and all-ignored cases need NEW tests in a temp git repository, which that plain-tempdir fixture cannot express. **(4)** A client ignore line that covers a whole artifact path (`.claude/`, `specs/`) makes everything the agent writes under it all-ignored, so by this rule it is the client's own and is not flagged.
**RECOMMEND the untracked-content rule:** it needs no flag and no checkpoint, adds no state, and treats what the client tracks or ignores as owned. **Cost:** one `git rev-parse --show-toplevel` call per check; one `git ls-files` call per artifact plus a no-regular-file walk; the tuple additions; new tests in a temp git repository for the tracked, ignored, untracked, empty and empty-subdirectories-only cases, and one for a source root that is a plain directory inside a temp git repository (the inside-the-wrapper fallback); prose at two remedy sites.
**Counter-argument, recorded:** with the untracked-content rule, an agent writing untracked files INTO a client-tracked `specs/` IS caught, because `ls-files` lists the untracked files. The strongest remaining objection: **the rule reads the index NOW, not at the task's start, so a client file that was untracked and unignored before the task is indistinguishable from one the agent wrote — the same bound as `FINDINGS.md` entry 11 — and nothing short of a pre-task snapshot (Alternative b) removes it.**

### D4 — The pre-commit hook: install where commits happen, find the install root, say when it skips, verify it is active (P4; F9)

**Proposal**, in four parts:
- **(i)** `/devforge:constitute` Phase 6.4 resolves the hook path with `git rev-parse --git-path hooks/pre-commit`, run in the repo whose commits carry code — the SOURCE repo in wrapper mode, the install root in standalone — so `core.hooksPath` is honoured.
- **(ii)** The hook template locates the install root by walking UP from `git rev-parse --show-toplevel` until a directory holds `.devforge/lib/constitute_helper` (wrapper: the parent), bounded at the filesystem root.
- **(iii)** When no helper is found, the hook prints ONE stderr line — `forcing-functions hook: no .devforge/lib/constitute_helper above <toplevel>; skipping` — and exits 0: a loud no-op.
- **(iv)** A new `constitute_helper verify-hook [--source-root <path>]` verb reports `{installed, path, executable, marker_present, active_hooks_path}`. Phase 6.4 runs it right after the copy, with its stdout shown verbatim, and `scripts/post-update-checks.sh` runs it too: that check returns silently today when the file is missing (`:110`), and will WARN when the install's `constitute.json` has an enabled rule and no active hook exists.

**Bounds, recorded.** **(1)** When `core.hooksPath` points INSIDE the source repo to a TRACKED directory (a husky-style `prepare`), copying the hook there puts a framework file into the client's history, which plan 97's content guard forbids in wrapper mode. Phase 6.4 must REFUSE in that case and tell the user (OQ-4). **(2)** The hook is opt-in, and the per-task gate already runs the detectors (F9); the hook guards only commits made outside `/devforge:implement`.
**RECOMMEND (i)–(iv).** **Cost:** a hook-template edit, Phase 6.4 prose plus one verb call, one verb with tests (temp git repos with and without `core.hooksPath`), one branch in `post-update-checks.sh`.
**Counter-argument, recorded:** **a hook that walks up directories can find a DIFFERENT install's `.devforge` when installs nest.** Bound the walk to one level above the toplevel (wrapper = parent) rather than to the filesystem root.

### D5 — `/devforge:review` grounding: (a) a line-scoped quote check in the shared validator, inherited by `/devforge:audit` and `/devforge:grill`; (b) produce the advertised `[CROSS-AGENT]` tag, or delete it (R5, K6; F10)

**(a) Proposal:** Check 3 of `validate_findings` (`_shared/_validate.py:119`) becomes line-scoped. The validator is SHARED: `/devforge:review` (`_review/_cli.py:309`), `/devforge:audit` (`_audit/_cli.py:653`) and `/devforge:grill` (`_grill/_cli.py:488`) each call it behind their `validate-findings` verb, so all three inherit the change. Today Check 3 tests the whitespace-normalised quote against the whitespace-normalised WHOLE file (`_validate.py:213`–`:219`), whose lines `_normalize_whitespace` (`:71`) joins with single spaces, so the line mapping is lost. The matcher becomes line-aware: the file is whitespace-normalised per line, a multi-line quote's window anchors on its FIRST line, and that first line must sit within a window of ±3 lines around `line`. A single-line quote matches as a whitespace-normalised substring of ONE file line; a multi-line quote matches when its first line is a suffix of a file line, its last line is a prefix of a later file line, and its middle lines equal the consecutive file lines between them (all whitespace-normalised). Today's token-level whole-file substring (`_validate.py:82`–`:83` tokenise the text and re-join it with single spaces; `:107` applies that to the whole file, and `:219` tests the quote as a flat substring of the result) accepts quotes that start and end mid-line, and the new matcher must keep accepting them.
- **`line_corrected`** — when it occurs outside the window and EXACTLY ONCE in the file, the validator KEEPS the finding, REWRITES `line` to the actual location (the quote's first line) and adds `line_corrected: {"from": N, "to": M}`.
- **`line_ambiguous`** — when it occurs outside the window two or more times, the validator KEEPS the finding with its `line` unchanged and flags it; when the per-line rules find it nowhere, the `line_unverified` fallback below decides.
- **`line_unverified`** — when the per-line match fails but today's whole-file token match (`:219`) succeeds — a quote whose line breaks differ from the file's, such as a re-wrapped long line or a dropped blank line — the validator KEEPS the finding with its `line` unchanged and flags it.
- **`quote_mismatch`** — when both matchers fail, the finding is discarded with reason `quote_mismatch`, exactly as today; it is the ONLY rejection Check 3 makes.
- The partner `file:line` of the emergent-issue checklist stays prose — recorded, not checked.

Each kept finding records its outcome as `line_outcome`: `corrected`, `ambiguous` or `unverified` for the three outcomes above, and `none` for a quote found within the window (Phase 4's render deliverable). The acceptance set is unchanged: every finding the old check accepted is still accepted; the new check adds line information the old check could not give.

**Alternative to (a):** a `--line-scoped` opt-in flag on `validate-findings`, so `/devforge:audit` and `/devforge:grill` keep today's whole-file rule and only `/devforge:review` passes the flag.

**(b) Proposal:** a `review_helper compute-consensus` verb that delegates to `_shared/_consensus.compute_consensus` exactly as `audit_helper` does (`_audit/_cli.py:664`–`:707`), called ONCE in 2.6 on the combined validated array, before refutation — one helper call per command, within the bound 128 F10 states, derived from stub plan 124's measurement. It wires `/devforge:review` only. The tag and the severity bump then exist there.
**Alternative to (b):** delete the dangling adverts — `/devforge:review`'s two (the `[CROSS-AGENT]` line in `review/references/report-format.md:53` and the preservation note at `_review/_report.py:134`) and `/devforge:grill`'s two (the preservation note at `_grill/_report.py:185`, *"[CONTESTED] and [CROSS-AGENT] tags are preserved from the finding's tags list"*, and the `[CROSS-AGENT]` entry in `grill/references/report-format.md:59`); grill calls no consensus either — one sentence each, honest.
**Bounds, recorded.** **(1)** The consensus key is the EXACT line (`_consensus.py:22`); after (a)'s correction, two finders citing the same defect at `:490` and `:492` merge only if correction lands both on one line — and a citation inside the ±3 window is kept as cited, not corrected, so those two stay apart. **(2)** The lesson's "same pointed question to two agents" is a dispatch pattern, not exact-line grouping; (b) delivers corroboration, not that pattern. **(3)** The four finders carry specialty briefs, so how often they overlap is unmeasured. **(4)** `/devforge:grill`'s findings quote plan and spec artifacts, where line drift between writing and refuting is common, so grill will see more `line_corrected` rows than review or audit (unmeasured). **(5)** Under wire, grill's two `[CROSS-AGENT]` adverts stay dangling: grill is design-level, and a `file:line` consensus key does not fit its artifacts, so wiring grill is out of scope here. **(6)** Refuter counter-quotes stay unchecked: `apply_verdicts` (`_shared/_verify.py:564`) is pure (reads no files; its docstring, `:590`: *"Does NOT re-derive a verdict or enforce the evidence rule."*), and a counter-quote sits at the guard or call site (`review/references/refutation-preamble.md:47`), not at the finding's line, so a line-scoped check would strip valid ones. **(7)** `line_unverified` and `line_ambiguous` findings carry a line nothing verified; they reach the orchestrator's view only through Phase 4's render deliverable — `line_outcome` on every kept finding, and one sentence in each of the three consumers' `main.md` listing the flagged rows in the validation summary.
**RECOMMEND (a) as one rule in the shared validator** — one validator, one rule, not the opt-in flag — **and (b)-wire for `/devforge:review` only** — consistency with `/devforge:audit`'s single-pass path (`--passes 1`); its multi-pass path replaces consensus with `_audit/_merge.py` (`12-AUDIT-MULTI-PASS-UNION-PLAN.md`). A dangling tag is a sentence-level hallucination risk either way; under wire, grill's two remain one (Bound 5). **Cost:** the validator change and its tests (including the `_generate_docs` precedent's line-range shape), with tests for all three consumers; the `line_outcome` field and one sentence in each of the three consumers' `main.md` (Phase 4's render deliverable); one verb and its registration, 2.6 prose, `report-format.md` wording. Under wire, `compute_consensus` COLLAPSES same-location findings — one representative per `(file, line, category)` group, carrying `merged_count` — and returns a dict holding `findings` and a `consensus_map` (`_consensus.py:120`–`:126`), so at 2.6 the validated array's shape and the finding count change. And `tests/lib/_review/test_report.py`'s `test_no_consensus_line_in_report` (`:421`–`:424`) and `test_no_consensus_line_in_inline_summary` (`:605`–`:608`), whose docstrings state *"/review has no compute-consensus step"*, change meaning under wire and are rewritten.
**Counter-argument, recorded:** **a flag the orchestrator can ignore changes nothing unless every consumer renders it (the Phase 4 render deliverable), and a corrected line can be WRONG when the unique occurrence elsewhere is a different site that happens to carry the same text — the correction is then a confident mis-citation, worse than the vague one it replaced.**

### D6 — Refutation gains a reachability criterion and a count / equivalence grounding rule (P9, R5; F11)

**Proposal:** three refutation preambles exist. The review and audit preambles (`src/commands/review/references/refutation-preamble.md`, `src/commands/audit/references/refutation-preamble.md`) are identical except at `:3` and `:6`. The third, `src/commands/grill/references/refutation-preamble.md`, is design-level: it cross-examines a devils-advocate attack on a plan + spec, and its `:11`–`:13` demand that the refuter *"demonstrate the defect from the quoted artifact in front of you — the plan, the spec, the cited constitution, the quoted source file, or the re-fetchable external citation"*. A grep for `reach|count|equivalen` over it finds no count or equivalence criterion (its `count` hits are `counter-quote` and the verdict-file format's `# Verdict count:` lines). The sentences go where they apply:
- **The REACHABILITY sentence — review and audit preambles only** (it is about code paths): *"A finding whose defect depends on a VALUE or STATE is confirmed only when you trace the site UP to a live construction, instantiation or call site (`trace_path`, or a grep you quote) and quote it; a path with no live producer is dismissed with reason `unreachable`."*
- **The COUNT / EQUIVALENCE sentence — review and audit preambles:** *"An equivalence claim (two guards, two queries), a reach claim or a count in a finding or a verdict is confirmed only by a run or a grep whose output you quote; a count is word-bounded (`grep -rlw`) and spans multi-line imports."*
- **Its grill variant — the grill preamble only.** Grill cross-examines an attack on a plan and a spec, so the variant drops the code-shaped words "a reach claim" and "multi-line imports" — with the code examples and the `grep -rlw` rule — and admits a quoted artifact passage as evidence: *"A count or an equivalence claim in a finding or a verdict is confirmed only by a quoted artifact passage, or by a run or grep whose output you quote."*

The review / audit difference at `:3` and `:6` is kept.

**RECOMMEND as proposed.** **Cost:** prose in three files — two sentences in each of the review and audit preambles, one in the grill preamble — with the review / audit difference preserved.
**Counter-argument, recorded:** **the refuter already defaults to dismiss, so a reachability demand mostly costs on CONFIRMATIONS — where cost belongs — but a refuter without CBM access (a consumer without the MCP) can only grep.** The sentence names grep as the fallback.

### D7 — Vacuous and not-run results reach `verification.md` as lines, never as blockers (P6; F4)

**Proposal:** `render-report` renders one line per gate with its status — in the home OQ-8 names — INCLUDING `off`, `inconclusive`, `vacuous`, `baseline-failing`, `e2e-clean`, and the D1 / D2 fields. `compute-verdict` adds reason lines, never blockers, for:
- a mechanical `pass` with an empty `test_commands_run` — the `/devforge:implement` wording, *"verification succeeded without a single test running"* (`implement/main.md:184`);
- skipped `N/A` commands;
- regression `inconclusive` / `baseline-failing`.

Dead-code `vacuous` (zero rows, `_dead_code.py:193`) is RENDERED as a gate line and gets NO reason line. The `report-format.md:103` sentence (*"writes nothing to `verification.md`"*) is reversed for the rendered line and kept for blockers. e2e keeps its existing reason line: `_verdict.py:520`–`:526` already appends *"E2E run ({status}, advisory — does not block the verdict): {note}"* for every non-`off` e2e status, `e2e-clean` included; the new e2e gate line renders the status only, and Phase 5's Verify checks that there is no duplicate.
**Bound, recorded:** an e2e suite with zero scenarios cannot be detected generically (that is runner-specific); recorded, not built.
**RECOMMEND as proposed.** **Cost:** render lines, verdict reason lines and their tests; prose in `report-format.md` and `verify/main.md` 5.1 / 5.2.
**Counter-argument, recorded:** **`report-format.md:103` keeps non-violation statuses out of the report ON PURPOSE, and every added line is read by the user at PHASE 8 and by whoever opens `verification.md` later; a longer report buys nothing when every status is `clean`.**

### D8 — Browser / API verification against a non-local runtime is observe-only; mutating flows name a disposable record or go MANUAL (W2; F17)

**Proposal**, in two parts:
- **(i) Mechanical.** `read-ac-config` (`def cmd_read_ac_config(args):`, `_verify/_cli.py:213`) classifies each runtime host — loopback (`localhost`, `127.0.0.1`, `::1`, `0.0.0.0`) → `runtime_scope: local`; anything else → `runtime_scope: shared` — and the PHASE 3 brief passes it. Under `shared`, the ac-verifier performs NO state-changing step (no `fill` / `click` that submits, no non-GET API call, no `evaluate_script` write) and records a mutating AC as `UNVERIFIED` with the reason *"mutating flow on a shared runtime; verify manually or name a disposable record"*.
- **(ii) Prose.** `src/agents/ac-verifier.md` gains the rule and the warning that a route can mutate ON LOAD and a print / export route can save a file; `/devforge:specify` Step 4.4 says that an AC whose action mutates state names the disposable record in its Given clause; `src/agents/design-auditor.md` keeps navigation (observe-only), with the on-load bound stated.

**Bounds, recorded.** **(1)** Observe-only navigation can still fire an on-load mutation; the host rule is the only mechanical tooth, and it is coarse. **(2)** A dev server on a non-loopback host (a container, the LAN) degrades to observe-only (OQ-3).
**RECOMMEND (i) + (ii).** **Cost:** one field in `read-ac-config`, brief prose, agent prose, one `/devforge:specify` sentence.
**Counter-argument, recorded:** **every consumer whose `ac_runtime_url` is a container hostname loses mutating verification, with no way back except editing `project-config.json`.** An override key would be a `/devforge:configure` question — a stop, which the bound 128 F10 states, derived from stub plan 124's measurement, rules out.

### D9 — A WARN-only secret scan over the feature directory, inside the finalize preflight (P11; F16)

**Proposal:** `preflight_context` (`_finalize/_preflight.py:214`) gains `secret_hits: [{file, line, kind}]` from a fixed pattern set run over `specs/<feature>/**`: private-key headers (`-----BEGIN … PRIVATE KEY-----`), `AKIA[0-9A-Z]{16}`, `Bearer [A-Za-z0-9._-]{20,}`, `(api[_-]?key|secret|token)\s*[:=]\s*['"]?[A-Za-z0-9_\-]{16,}`, `import.meta.env`, `process.env.`. `/devforge:finalize` shows the hits verbatim before its commit step and proceeds — a WARN, no stop, no blocker. No new helper call: the preflight already runs.
**Bounds, recorded:** regex scanning is noisy and misses structured secrets; a project running `gitleaks` has a better tool, and the WARN says so. `/devforge:configure` reading `.env*` contents into context (F16) is recorded as a bound, not changed here. The scan runs too late to keep a secret out of history: intake and `/devforge:specify` WIP-commit what they write under `specs/<feature>/` as they write it (the workflow list in `src/CLAUDE.md`, `:55`–`:57`; the later artifact-writing commands, `:58`–`:61` and `:63`–`:66`, do too; `:62`, `/devforge:implement`, carries no such clause), so a hit found at finalize is already in WIP commits — the finalize squash rewrites them, but a WIP commit already pushed is not recalled. And `process.env.` / `import.meta.env` match ordinary spec prose that names a configuration variable, so the WARN will be noisy.
**RECOMMEND as proposed.** **Cost:** one function and its tests, one prose paragraph.
**Counter-argument, recorded:** **a WARN the orchestrator narrates and commits past is near-zero protection**; a blocking gate would be a stop.

### D10 — ac-verifier never re-runs the gates; fix its self-contradiction (K1; F3)

**Proposal:** the `ac-verifier.md:3` description drops "run the test suite under tests" for "read the changed files under tests (the orchestrator runs the suite)"; `:131` is reworded to match `:38`; and the file's `## Rules` section (`:124`) gains *"Never run build, type-check, lint or test commands — the orchestrator runs them once in PHASE 4; your evidence is observation and code-reading."* `/devforge:verify`'s 3.3 brief carries the same sentence.
**Alternative declined:** reorder PHASE 4.1 before PHASE 3, to hand the logs to the agent. The agent's contract is code-reading; the logs are the orchestrator's signal.
**RECOMMEND as proposed.** **Cost:** prose.
**Counter-argument, recorded:** **an agent with Bash will still run `grep` / `sed`; the rule names the four command classes, not Bash.**

### D11 — Guidance sentences, one per site, each a hallucination-check item (P9, P10, P13, K2, K3, K4, K5, W3)

**Proposal:** six sites gain these sentences.
- **`/devforge:fix`** (`src/commands/fix/main.md`, the agent brief near `:332`): *"A fix needs a test when the defect is a nullability or runtime-only difference (`.map` vs a null-safe chain, in-place mutation); an assignability error is guarded by the type gate. The test must fail without the fix."* and *"Before repairing a guard, comparator or formatter, run `git log -S '<guard text>' -- <file>` and read the diff that removed it; verify a cited precedent commit by its DIFF, never its subject."*
- **`/devforge:breakdown`** ordering (`:262`): *"the type checker stays green between tasks: a repair task precedes the migration task that removes the old gate, so the new gate is green on arrival"*; and test strategy near `:405`: *"cover the integration layer (handlers, visibility, the full prop contract of a stubbed child) and the fall-through branch of every new early-return guard; extract a heavy loop into a pure function and test that — a table-driven test over one field covers that field, not the loop."*
- **`/devforge:specify`** Step 4.4 (near `:663`): *"A data-shape criterion asserts VALUES, never the presence of a field."*
- **`/devforge:plan`** sub-question 9 (`:437`): *"compute the closure on the import graph — re-exports and barrels included; a class-name search is a floor, not the closure."*
- **`implement/references/agent-brief.md:18`**, self-repair: *"The repair edits source and tests only — never a generated or gitignored artifact (a built `dist/`), a configured command, a lint/type configuration or suppression, or the test being run. When the failing command is itself wrong, stop and say so (the `tooling_unavailable` path, `implement/main.md`)."*
- **`src/agents/qa-engineer.md`** (near `:45`) and **`src/agents/qa-reviewer.md`** (near `:27`): *"pair every negative assertion with a positive one; mount a second, distinct fixture value so a hardcoded literal cannot pass."*

**RECOMMEND all six.** **Cost:** prose; each sentence must satisfy the sentence-level hallucination check (mechanically true or verifiable).
**Counter-argument, recorded:** **prose rules are unmechanical; the data shows prose memory rules were what WORKED at that installation — and also what accumulated to 259 KB (the installation's own figure; an illustration, not measured here).**

### D12 — The task template's lint line: decline a text change (P12; F5)

**Proposal — decline:** no text change. A package-level lint run is a superset of the package's changed files, so the template line *"Linter passes on changed files (see Development Commands section)"* (`breakdown_helper.py:1007`, `storage-rules.md:241`) is IMPLIED by the mechanism, not contradicted by it. `src/CLAUDE.md:221`, Always-rule 8 — *"**Lint everything** — linting must pass on all changed files before task completion"* — is an instruction to the agent, also not false. The lesson's actual ask — "no NEW warnings in changed files, measured per file before and after" — is a warning DELTA the mechanism does not compute (F5), and that delta is runner-specific (declined in `## Non-goals`).
**Read-only note — the tests that pin the template line; no phase edits them:** `tests/lib/test_breakdown_helper.py` at five sites (`:1837`, `:1854`, `:1875`, `:1949`, `:1978`), `tests/lib/_implement/test_handoff_reader.py:188` and `tests/lib/_implement/test_cmds_resolve.py:180`.
**Bound, recorded:** the superset holds only as far as the configured `lint_command` reaches — the module's own example, `npx eslint src/` (`_cmds_verify.py:99`), does not lint a changed file outside `src/`.
**RECOMMEND decline.** **Cost:** none.
**Counter-argument, recorded:** **a consumer reading "on changed files" expects per-file evidence the report never shows.**

### D13 — `verify-touched` builds the touched packages before type-checking when the touched set spans ≥ 2 packages (S2; F5)

**Proposal:** in `cmd_verify_touched`, when `touched_files` resolve to two or more packages, the order is build (touched packages) → type-check → lint → test; a single package keeps today's order, failing fast on static checks. Six existing statements of today's fixed order become false under D13, so all six are edit targets, corrected in the same phase:
- `src/CLAUDE.md:175` (scope-aware verification step 4 — *"The fixed order is static checks (type-check + lint) → build → tests, so a failing build surfaces before any test runs."*);
- `src/commands/implement/main.md:182` (*"It runs them in a fixed order: static checks (type-check + lint) first, then the build once, then tests last"*);
- `src/commands/fix/main.md:346` (*"runs that package's static checks (type-check + lint) → build → tests"*);
- `src/commands/verify/main.md:243` (PHASE 4.1, *"runs that package's commands in the fixed order static checks (type-check + lint) → build → tests"*);
- `src/devforge/lib/_implement/_cmds_verify.py:26`, the module docstring (*"static checks → build → tests; a broken build surfaces first"*);
- `_cmds_verify.py:619`–`:622`, the comment above `all_cmds` (*"All commands to run: type-check, then lint, then build, then test."* … *"A broken build surfaces first"*).

Correcting them is truth maintenance of existing statements; plan 128's *"No `src/CLAUDE.md` edit"* non-goal (`128-AC-VERIFICATION-COMMAND-GATE-PLAN.md:388`) is about adding always-on obligations and does not cover it.
**RECOMMEND.** **Cost:** an ordering branch and its tests; the six order statements. **Coordination:** plan 116 (a stub) owns per-package command COMPOSITION; this is ORDER inside the same function.
**Counter-argument, recorded:** **single-stack evidence (`[NPM]`); builds are slow, and a red type-check that a build would have cured is rare outside compiled multi-package workspaces.**

### D14 — The memory entry shape, in the PHASE 7 rubric and the template comments (R3; F15)

**Proposal:** PHASE 7 states the entry SHAPE — `- **[TAG]** YYYY-MM-DD — <at most two lines> — <pointer: specs/<feature>/…>` — and two rules: *"when a fact an entry states has changed, delete that entry and re-insert the corrected entry, re-dated, at the end of its section (immediately BEFORE the next `## ` heading); never append a contradicting entry beside the stale one"* and *"never cite another entry by its position ('the third pitfall above')"*. A correction is delete-and-re-insert, not an in-place rewrite, because the excerpt's cut keeps a section's LAST lines — `src/devforge/lib/_shared/memory.py:393`–`:395`: *"a truncation keeps the LAST `alloc` content lines -- both memory.md writers append, so the newest lines are the trailing ones"* — so the re-inserted entry is kept as the newest. "Never cite by position" is a readability rule, unrelated to the excerpt mechanics. The comments in `src/devforge/memory.md` carry the same shape. No size cap, no entry cap, no consolidation (128 D9 (b)).
**Alternative considered:** fold the entry-shape recommendation into 128 D9 (b)'s `FINDINGS.md` entry as recorded guidance, building nothing.
**Bound, recorded:** an in-place rewrite that keeps the old position would be the first line cut under truncation; hence delete-and-re-insert.
**RECOMMEND.** **Cost:** prose in one command, plus the template comments. **Coordination:** 128 D9 (a) declines the sibling session's proposed SECTION, and D9's heading says "no rubric change" (`128-AC-VERIFICATION-COMMAND-GATE-PLAN.md:148`); D14 departs from that phrase on the entry shape and its two rules only — the three buckets (128 `:150`; `src/commands/verify/main.md:384`–`:386`) and the skip-silently rule (`verify/main.md:380`, `:388`) stand. 128's non-goal *"No memory template or PHASE 7 rubric change"* (128 `:385`) is departed from on the same terms: D14 edits the template's comments and the rubric's entry shape, and adds no section and no bucket. 128's `FINDINGS.md` entry (its D9 (b)) may be amended at this plan's ledger phase with the installation's own figures (354 entries / 259 KB; an illustration, not measured here).
**Counter-argument, recorded:** **the rubric already says "sharpen or extend the existing wording" (`:378`); the shape adds ceremony that the 120-line excerpt budget then truncates.**

### D15 — The inner-repo ignore line: record the anchoring rule for plan 115; correct `DEVELOPMENT-STATUS.md:83` (P2; F18)

**Proposal:** build nothing. **(a)** `DEVELOPMENT-STATUS.md:83`'s claim is corrected, in the ledger phase, to what the tree does: the wrapper substep asks which folder is the source root and writes no ignore line. **(b)** The `115-WRAPPER-INNER-REPO-CBM-VISIBILITY-PLAN.md` stub gains one paragraph: whatever ignore entry 115 writes must be ANCHORED (`/<inner>/`), because an unanchored `<inner>/` also ignores `docs/<inner>/`, which `/devforge:finalize`'s `git add docs/` (`finalize/main.md:154`) would then silently miss.
**RECOMMEND.** **Cost:** two ledger edits.
**Counter-argument, recorded:** **editing another plan's stub from this plan crosses ownership**; the alternative is a `FINDINGS.md` cross-reference only.

### D16 — `FINDINGS.md` entries (K5, K9, W3)

**Proposal:** three ledger changes, each in the entry shape F22 describes.
- **(a) AMEND entry 11 in place:** `capture-touched-files` cannot see edits to gitignored files (no `--ignored`), so a self-repair edit to a built artifact is invisible to the review panel and the WIP commit — inferred from git behaviour; nothing run.
- **(b) A NEW entry:** docs prose identifiers are never resolved — only citations `/devforge:generate-docs` registers are checked (`_validators_file_doc.py:185`); the tech-writer rule is instruction-only; a phantom name survives in any doc.
- **(c) A NEW entry:** `/devforge:implement` has no stop-and-amend-spec path. The only route is `/devforge:verify` NEEDS WORK → a fresh specify cycle (`verify/main.md:183`); a task whose measured ladder breaks on something the spec could not see has `repair` / `skip` / `stop` only.

**RECOMMEND.** **Cost:** ledger text. The new entries' numbers (13 and 14 against 2026-10-05's 12 entries) are re-derived at build time, after 128's D9 (b) entry lands.
**Counter-argument, recorded:** **an ownerless entry is where a problem goes to wait, not to be fixed — `FINDINGS.md` holds twelve already and no command reads it; recording (b) and (c) without an owner is the honest minimum, not progress.**

### D17 — Queue position and coordination with 128

**Proposal:** 131 builds after 112–130, in numeric order — no jump. Plan 128 lands first and edits `verify/main.md` (Important rules item 12, PHASE 4.6), `specify/main.md` Step 4.4 and its rule 13, `report-format.md`, `_verdict.py`, `_report.py` and `_cli.py` (registry 16 → 17), so every anchor here drifts; re-anchor by quoted text. 128's D9 (b) `FINDINGS.md` entry will exist by then, as D14's amendment target.
**RECOMMEND no jump.** **Cost:** every gap above stays open until the queue reaches 131.
**Counter-argument, recorded:** **D3's false positive gate-blocks EVERY task on a wrapper install whose inner repo carries its own `.claude/` or `CLAUDE.md`, and plan 125 is the precedent for a ratified queue jump on a shipped defect (`125-VERIFY-FILE-BUGS-IMPORT-PLAN.md`, its D5) — the maintainer may jump D3 alone.**

### D18 — What stays out, by name

**Proposal:** R1 and R2 (tooling), P7's remainder, P8, S1, S3–S15, K8's techniques, K10, W4, E1, E2, N1, N2 and the auto-memory block stay with the consumer. No `references/stack-notes/` file is created — the sender's guidance; a reference file that no command reads is dead weight and a hallucination surface. The data's `forge-active-line-is-2-0` entry holds on 2.0 by documented policy (F19); no preservation of command edits is built.
**RECOMMEND.** **Cost:** none.
**Counter-argument, recorded:** **the 25 OUT rows are the largest single bucket of the dataset (25 of 54), each a lesson distilled from that installation's memory; leaving all of them out discards nearly half of what was handed over, and the declined alternative — a `references/stack-notes/` file — is declined, beyond the sender's guidance, only because nothing in 2.0 reads one.**

### OQ-1 — D3: does the orchestrator hold the checkpoint sha at PHASE 5? *(ANSWERED by the tree, 2026-10-05 — no outcome needed)*

**Verified 2026-10-05: yes.** `/devforge:implement`'s `## PHASE 2: Preflight + checkpoint + WIP marker` (`implement/main.md:108`) captures preflight's `head_sha` — *"the **source** repo HEAD"* — as the task's checkpoint SHA (`:116`), and *"Then the orchestrator creates the pre-task checkpoint and writes the WIP marker"* (`:131`). PHASE 0's `rollback` and `skip` arms use it as `<checkpoint_sha>`, *"the `**Checkpoint**:` field, which is the **source** repo HEAD"* (`:68`–`:69`), and PHASE 4 already passes it as `capture-touched-files --checkpoint <checkpoint-sha>` (`:165`), before PHASE 5 (`:174`). So a checkpoint-keyed D3 would have had a ready value. The rule as now drafted (D3's untracked-content rule) consumes no checkpoint sha, so this answer is recorded and unused.

### OQ-2 — D1's runner table: which runners

**RECOMMEND** pytest, vitest, jest, go test, cargo test and rspec, with the loud fallback for the rest.

### OQ-3 — D8's override for non-loopback dev servers

**RECOMMEND none in this plan** — no new `/devforge:configure` question; the degradation is recorded (D8's Bound 2 and counter-argument).

### OQ-4 — D4 when `core.hooksPath` is a tracked directory inside the source repo (wrapper)

Refuse and tell the user, or write the hook anyway.
**RECOMMEND refuse** (D4's Bound 1).

### OQ-5 — D5 (b): wire the consensus, or delete the tag

**RECOMMEND wire, for `/devforge:review` only.** Grill's two `[CROSS-AGENT]` adverts (`_grill/_report.py:185`, `grill/references/report-format.md:59`) stay out of scope under wire (D5's Bound 5): grill calls no consensus, and a `file:line` consensus key does not fit its design-level artifacts. **Alternative:** delete, as D5 states — review's two adverts and grill's two.

### OQ-6 — The `CHANGELOG.md` sub-headings

D3 (a false positive), D5 (a dangling tag), D10 (a contradiction) and D15 (a stale ledger claim) are `### Fixed`; the rest are `### Changed`. D12 (declined) changes nothing and gets no line.
**RECOMMEND split lines accordingly.** ⚠ **Re-verify the sub-headings LIVE at build time, and never edit a released version block.**

### OQ-7 — One plan or two

The mechanical decisions (D1–D9, D13) and the prose decisions (D10, D11, D14) could ship as two plans; D12 declines any change and ships in neither.
**RECOMMEND one plan with per-build-area phases**, because the disposition table is the shared artifact. **Alternative:** a split, at the maintainer's pick.

### OQ-8 — D7's rendering home

Lines under `## Code Quality` (`verify/references/report-format.md:42`), or a new `## Gates` block.
**RECOMMEND `## Gates`** — one line per gate; blockers unchanged.

### Phase 0 close record

**OPEN — nothing ratified.** No decision and no open question above has an outcome (OQ-1 is answered by the tree), and **no build phase may start.** ⚠ **Nothing is built and nothing is measured.**

When the record closes, it is written in the shape of plan 125's close record (`125-VERIFY-FILE-BUGS-IMPORT-PLAN.md`, `### Phase 0 close record`): the occasion; the directive, with any non-English directive given in English translation; the pick-or-delegation classification per `98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md`'s D1 distinction; and an outcomes table.

#### Verify

- The record names **each** of D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D13, D14, D15, D16, D17, D18, OQ-1, OQ-2, OQ-3, OQ-4, OQ-5, OQ-6, OQ-7 and OQ-8 **by name, never against a range**. Every D and each of OQ-2 to OQ-8 carries an explicit outcome (ratified / amended / declined); OQ-1 is recorded as answered by the tree, with no outcome needed.
- **D3's outcome names the rule form:** the untracked-content rule (the proposal), content-keyed (alternative a) or snapshot (alternative b).
- **D4's outcome names the walk-up bound:** one level above the toplevel, or the filesystem root.
- **D5's outcome states (a) and (b) separately: (a) as the single rule in the shared validator or the `--line-scoped` opt-in flag, and (b) as wire or delete.**
- **D8's outcome names the host rule** — the loopback set D8 lists, or an amended one.
- **D14's outcome names the form:** a rubric change (the proposal) or a fold into 128 D9 (b)'s `FINDINGS.md` entry (the alternative).
- **D17's outcome states jump or no jump explicitly.**
- **OQ-7's outcome states one plan or a split**, and on a split names which decisions go to which plan.
- **Each outcome states whether it is an explicit maintainer pick or a delegation.**
- **Every counter-argument, every Bound line and every Alternative above is still present, unshortened.** Phase 0's lead-in *"Nothing below is ratified."* stays as written, with a dated parenthetical beside it naming the close.

---

## Phases

Phase 0 is the section above; **nothing below starts before its close record exists.** **Build order: Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8** — one build area per phase (Phase 2 edits `/devforge:implement`, `/devforge:fix`, `/devforge:verify` and `src/CLAUDE.md`; Phase 4 reaches `/devforge:review`, `/devforge:audit` and `/devforge:grill` through the shared validator, the render sentences and the preambles; Phase 5 edits `/devforge:verify`, `/devforge:specify`, two agents and the memory template; Phase 7 touches several commands' prose), guidance sentences after the mechanisms, the ledgers last. Phase 5 follows Phase 1 because D7 renders the fields D1 and D2 add; Phase 8 records what Phases 1–7 built. If OQ-7's outcome splits the plan, this section is rewritten to the split before any build. Every phase builds only what its decisions' ratified outcomes name.

Every phase commits by explicit path — **never `git add -A`** — because other sessions build in this checkout. Commit subjects take the `<type>(plan-131): Phase N — …` form, matching the repo's existing style: on 2026-10-05 the HEAD subject read `docs(plan-111): Phase 4 — …`.

**House rules for every phase.**
- Python edits route **python-engineer → python-reviewer**, and markdown edits route **instruction-author → instruction-reviewer**; each loop runs until its review is clean.
- Every helper function gets its own test, written AND run in the same turn.
- Tests round-trip through real producers: runner-output fixtures are real runner output samples, never hand-authored imitations.
- A test that needs a git history — the regression worktree, the isolation check, the hook — builds its own temp git repository, never this repo's tree.
- Exact test output is read via `rtk proxy` plus a file redirect, never from the display (Trap 10).
- Commits name their paths (`git commit -m … -- <paths>`), never `git add -A`; after each commit, `git show --stat` lists only that phase's files and this plan.

### Phase 1 — `/devforge:verify`'s regression gate (D1, D2, OQ-2)

**Route: python-engineer → python-reviewer for `_regression.py`, `_verdict.py` and the tests; instruction-author → instruction-reviewer for `src/commands/verify/main.md` 4.3 and `verify/references/report-format.md`.**

#### Deliverables

- **`src/devforge/lib/_verify/_regression.py`** — D1's full-output capture (byte-capped), extraction table with OQ-2's runners, Counter diff, statuses and JSON fields; D2's new-test run in the same worktree; `_run_test_cmd` stops collapsing a timeout, an `OSError` and the catch-all `Exception` into `(1, …)` (`:308` *"Never raises"*, `:322`–`:327`): it returns a distinct not-run outcome (a typed or sentinel return) that D1's two runs and D2's per-file and combined runs read, and its existing callers are updated — grep `_run_test_cmd` at build time to name them. `_run_test_cmd` also maps exit 126 and 127 — the not-executable codes `_e2e.py:154` already names — to the same not-run outcome, so D1's two runs and D2's runs read ONE signal for every not-run cause. Whatever its form, that outcome keeps which cause it was — exit 126, exit 127, a timeout or an exception — because D1's `note` names the arm and D2's rows record `exit` 126 or 127, or `exit: null` for a timeout or an exception.
- **`src/devforge/lib/_verify/_verdict.py`** — D2's one reason line.
- **`src/commands/verify/main.md`** `### 4.3 — Full-suite regression gate` and **`verify/references/report-format.md`** `## Regression gate` — the new statuses and fields.
- **Tests** under `tests/lib/_verify/`, with real runner output samples committed under `tests/lib/fixtures/`.
- **This plan** — `#### Phase 1 record` below.

#### Verify

- The gate's JSON carries `baseline_failures`, `head_failures`, `new_failures` and `extraction`, and D2's `new_tests` (an array of `{file, exit, passes_without_change, output_tail}` rows), `combined` (bool), `new_test_files` (the count) and `falsification` (`ran`, `not_run` or `n/a`).
- **`regression` fires on a red baseline** when HEAD adds a new failing name, in a temp repo whose baseline already fails one test.
- **The loud fallback:** an unknown runner, and a non-zero exit with zero extracted names, each yield exit-code semantics with `extraction: none` and a note.
- A baseline run that ends in exit 126 or 127, a timeout or an exception yields `inconclusive` with the arm named, never `baseline-failing`, and a HEAD run that ends the same way yields `inconclusive`, never `regression` — each arm tested with its own case, exit 126 and exit 127 separately. `tests/lib/_verify/test_regression.py`'s `test_worktree_cleanup_after_exception` (`:439`–`:459`) patches `_run_test_cmd` itself to raise and expects `inconclusive`, which the outer catch (`_regression.py:350`–`:352`) produces, not the three arms; it still passes or is updated to the new return shape.
- A duplicate test title failing twice at HEAD and once at the baseline yields one `new_failures` entry (Counter, not set).
- An output larger than the byte cap is truncated and the note declares the cap.
- **D2:** a new test file that passes at the merge-base gets a `new_tests` row with `passes_without_change: true` and adds exactly one reason line and no blocker; a new test that fails there gets a row with `passes_without_change: false`, and so do a new test that fails collection there (pytest exit 2) and a run whose runner rejects the file argument — in each case `falsification` stays `ran` and the row's `output_tail` holds the last 200 characters of that run's combined output; `new_test_files` equals the number of `new_tests` rows; with three new test files whose first fails, the other two still run and each gets its own row; with 10 or fewer new test files, each merge-base run receives exactly one new test file's path and `combined` is `false`; with 11, ONE combined run receives all 11 paths and no others, the JSON records `combined: true`, every `new_tests` row carries that run's `exit` and `output_tail` and `passes_without_change: null`, and the reason line says the result covers the set when that run exits 0, and no reason line when it exits non-zero.
- **`falsification`, each value tested:** `ran` for per-file runs and for a combined run, including runs that exit non-zero with any code but 126 or 127; `not_run` for a missing command (exit 127), a command found but not executable (exit 126), a timed-out run (`subprocess.TimeoutExpired`, `_regression.py:322`) and any other exception raised by the run (`OSError` at `:324` or the catch-all `Exception` at `:326`) — the timeout and both exception arms recognised by the exception, never by the exit code, and each tested with its own case — each with that invocation's row carrying `passes_without_change: null`, `exit: null` for the timeout and the exception rows, `exit: 127` for the missing command and `exit: 126` for the not-executable command; in a set where one invocation could not run, the rows that ran keep their values, and a `true` row among them still gets the reason line; `n/a` when `new_test_files` is 0, with `new_tests` `[]` and no reason line.
- **No new verb:** `tests/lib/_verify/test_preflight.py`'s registry pin is untouched by this phase.
- Every new function has a test, written and run in the same turn.
- **Targeted first:** `python3 -m pytest tests/lib/_verify -q` is green. **Then the full suite:** `python3 -m pytest tests/lib -q` is green.
- `git show --stat` lists only this phase's files and this plan.
- python-reviewer and instruction-reviewer each return SHIP-READY, or every finding is fixed.

#### Phase 1 record

**NOT STARTED.**

### Phase 2 — `/devforge:implement`'s verify and brief (D3, D13, D11's self-repair sentence)

**Route: python-engineer → python-reviewer for `_cmds_verify.py` and the tests; instruction-author → instruction-reviewer for `src/commands/implement/main.md`, `src/commands/fix/main.md`, `src/commands/verify/main.md`, `implement/references/agent-brief.md` and `src/CLAUDE.md`.**

#### Deliverables

- **`src/devforge/lib/_implement/_cmds_verify.py`** — the rule form D3's outcome names, `.devforge` and `tickets` in `ISOLATION_ARTIFACTS`, and D13's ordering branch in `cmd_verify_touched`; the module docstring's order (`:26`) and the comment above `all_cmds` (`:619`–`:622`) state D13's ≥ 2-package rule.
- **`src/commands/implement/main.md`** — the `isolation_failure` remedy text (`:187`) names the rule; the fixed-order sentence (`:182`) states D13's ≥ 2-package rule.
- **`src/commands/fix/main.md`** — the same `isolation_failure` remedy text (`:351`) names the rule; the order clause at `:346` states D13's ≥ 2-package rule.
- **`src/commands/verify/main.md`** — PHASE 4.1's fixed-order clause (`:243`) states D13's ≥ 2-package rule.
- **`src/CLAUDE.md`** — scope-aware verification step 4's fixed-order sentence (`:175`) states D13's ≥ 2-package rule.
- **`implement/references/agent-brief.md`** — D11's self-repair sentence at `:18`.
- **`tests/lib/_implement/test_cmds_verify.py`** — NEW isolation tests in a temp git repository for the tracked, ignored, untracked, empty and empty-subdirectories-only cases, and one for a source root that is a plain directory inside a temp git repository (Trap 4); plus D13's ordering tests.
- **This plan** — `#### Phase 2 record` below.

#### Verify

- **Rule form:** the isolation items below are stated for the untracked-content rule; when D3's outcome names another form, they are rewritten to that form before the build.
- **Isolation, owned:** in a temp source git repository, an `ISOLATION_ARTIFACTS` entry whose content is all tracked, or all ignored, is NOT flagged.
- **Isolation, fresh:** an entry holding at least one untracked, unignored file — a fresh `.claude`, `CLAUDE.md`, `.devforge` or `tickets`, or an agent-written `.claude/commands/devforge/` inside a client-tracked `.claude/` — IS flagged, and an EMPTY entry directory — one holding no regular file at any depth, including one holding only empty subdirectories — IS flagged.
- **Fallback:** when `git -C <source_root> rev-parse --show-toplevel` does not resolve to `<source_root>` itself — `<source_root>` is not a git repository, or it is a plain directory inside the wrapper repository — today's existence check runs unchanged; a test covers the inside-the-wrapper case with a source root that is a plain subdirectory of a temp git repository.
- `test_claude_md_found` and `test_dot_claude_dir_found` are unchanged and green — their meaning holds (D3's Bound 3, Trap 4); no test is deleted.
- **Remedy text:** the `isolation_failure` remedy texts in `src/commands/implement/main.md` and `src/commands/fix/main.md` both name the rule.
- **D13:** a touched set spanning two packages runs build before type-check; a single-package set keeps type-check → lint → build → test. All six order statements D13 lists — `src/CLAUDE.md`'s scope-aware verification step 4, `src/commands/implement/main.md`'s fixed-order sentence, `src/commands/fix/main.md`'s order clause, `src/commands/verify/main.md`'s PHASE 4.1 clause, and `_cmds_verify.py`'s docstring and comment — state the ≥ 2-package rule.
- **D13 sweep:** a post-edit case-insensitive grep for `fixed order` and `static checks` across `src/`, `tests/` and `scripts/` returns, among the lines about `verify-touched`'s command order, only lines that state the ≥ 2-package rule. The hits about other orders are not D13's; on 2026-10-05 they are `src/commands/pr-review/main.md:29`, `src/commands/configure/main.md:335`, `src/commands/research/main.md:1338`, `src/devforge/lib/_discover/_cmds_core.py:297` and `src/devforge/lib/_discover/_cmds_design.py:254`.
- D11's self-repair sentence greps back verbatim from `agent-brief.md`.
- Every new function has a test, written and run in the same turn.
- **Targeted first:** `python3 -m pytest tests/lib/_implement -q` is green. **Then the full suite:** `python3 -m pytest tests/lib -q` is green.
- `git show --stat` lists only this phase's files and this plan.
- python-reviewer and instruction-reviewer each return SHIP-READY, or every finding is fixed.

#### Phase 2 record

**NOT STARTED.**

### Phase 3 — `/devforge:constitute`'s pre-commit hook (D4, OQ-4)

**Route: python-engineer → python-reviewer for the `verify-hook` verb, the hook template and `scripts/post-update-checks.sh`; instruction-author → instruction-reviewer for `src/commands/constitute/main.md` Phase 6.4.**

#### Deliverables

- **`src/git-hooks/pre-commit-forcing-functions.sh`** — the walk-up with the bound D4's outcome names, and the one-line stderr skip.
- **`src/devforge/lib/_constitute/_cli.py`** — the `verify-hook` verb, registered where `constitute_helper`'s verbs are registered (`src/devforge/lib/constitute_helper.py` is the entry point and imports `main` from `_constitute`). **`tests/lib/test_constitute_helper.py`** — its tests.
- **`src/commands/constitute/main.md`** `### Phase 6.4` — the resolved hook path, the refuse path per OQ-4, and the `verify-hook` call with its stdout shown verbatim.
- **`scripts/post-update-checks.sh`** — the WARN branch in `forge_check_precommit_hook`.
- **This plan** — `#### Phase 3 record` below.

#### Verify

- **Placement:** in temp repos with and without `core.hooksPath`, Phase 6.4's resolved path equals `git rev-parse --git-path hooks/pre-commit` in the repo whose commits carry code; in a wrapper fixture, that is the source repo.
- **Refuse path:** with `core.hooksPath` pointing at a tracked directory inside the source repo, Phase 6.4 behaves as OQ-4's outcome names, and no file is written into the client's history.
- **Loud no-op:** with no helper above the toplevel, the hook prints exactly one stderr line and exits 0.
- **Walk-up bound:** in a fixture with two nested installs, the hook does not reach past the bound D4's outcome names (Trap 12).
- `verify-hook` reports `installed`, `path`, `executable`, `marker_present` and `active_hooks_path` for an installed, a missing and a non-executable hook.
- `post-update-checks.sh` WARNs when `constitute.json` has an enabled rule and no active hook exists, and stays silent otherwise.
- **No registry `len()` pin to move (check at build):** a 2026-10-05 grep of `tests/lib/test_constitute_helper.py` and `tests/lib/_constitute/` finds no `len()` assertion over `constitute_helper`'s verbs; the build re-checks before adding the verb.
- Every new function has a test, written and run in the same turn.
- **Targeted first:** `python3 -m pytest tests/lib/_constitute tests/lib/test_constitute_helper.py -q` is green. **Then the full suite:** `python3 -m pytest tests/lib -q` is green.
- `git show --stat` lists only this phase's files and this plan.
- python-reviewer and instruction-reviewer each return SHIP-READY, or every finding is fixed.

#### Phase 3 record

**NOT STARTED.**

### Phase 4 — The shared validator, `/devforge:review`'s consensus and the refutation preambles (D5, D6, OQ-5)

**Route: python-engineer → python-reviewer for `_shared/_validate.py`, `_review/`, `_grill/_report.py` (delete arm only) and the tests; instruction-author → instruction-reviewer for `src/commands/review/main.md`, `src/commands/audit/main.md`, `src/commands/grill/main.md`, `review/references/report-format.md`, `grill/references/report-format.md` (delete arm only) and the three refutation preambles.**

#### Deliverables

- **`src/devforge/lib/_shared/_validate.py`** — D5 (a)'s line-aware Check 3 (per-line whitespace normalisation, D5 (a)'s single-line and multi-line match rules, a multi-line quote anchored on its first line, the ±3 window), `line_corrected`, `line_ambiguous` and the `line_unverified` whole-file fallback; `/devforge:review`, `/devforge:audit` and `/devforge:grill` inherit it.
- **The render deliverable for the three line flags.** The `validate-findings` JSON carries, on each finding in `passed`, `line_outcome` (`corrected` / `ambiguous` / `unverified` / `none`) beside the existing fields. ONE sentence each, at the step that runs `validate-findings`, tells the orchestrator to list the `corrected` / `ambiguous` / `unverified` rows in its per-finder validation summary: `src/commands/review/main.md` `### 2.4 — Consume + validate per finder, then combine` (`:191`; the call at `:200`); `src/commands/audit/main.md` `### 4.1 — Consume + validate per agent, then combine` (`:312`; the single-pass call at `:321` and the per-pass call at `:334`); and `src/commands/grill/main.md` `## PHASE 3 — Validate (the grounding gate) + union the two passes` (`:190`; the call at `:203`), where the summary is per pass, because grill validates one adversary's two passes. No validation summary exists in any of the three files on 2026-10-05 — a grep for `validation summary` over `src/commands/review`, `src/commands/audit` and `src/commands/grill` returns nothing — so each sentence creates one.
- **Tests for the shared validator and all three consumers** — the line-scoped unit cases in `tests/lib/_shared/test_validate.py`; each consumer's `validate-findings` path in `tests/lib/_review/test_brief.py` (review's round-trip through the real `validate_findings`), `tests/lib/_audit/test_cli.py` (audit), and `tests/lib/_grill/test_cli.py` with `tests/lib/_grill/test_merge.py` (grill).
- **D5 (b), per OQ-5's outcome** — wire: `review_helper compute-consensus` in `src/devforge/lib/_review/_cli.py`, one call in `review/main.md` `### 2.6`, and `tests/lib/_review/test_report.py`'s `test_no_consensus_line_in_report` (`:421`–`:424`) and `test_no_consensus_line_in_inline_summary` (`:605`–`:608`) rewritten to the wired report; or delete: review's `review/references/report-format.md:53` tag line and `_review/_report.py:134` note, and grill's `_grill/_report.py:185` note and `grill/references/report-format.md:59` tag entry.
- **`review/references/refutation-preamble.md`** and **`audit/references/refutation-preamble.md`** — both D6 sentences (reachability, and count / equivalence).
- **`grill/references/refutation-preamble.md`** — D6's grill variant of the count / equivalence sentence only.
- **This plan** — `#### Phase 4 record` below.

#### Verify

- **Rule form:** the D5 (a) items below are stated for the single rule in the shared validator; when D5's outcome names the `--line-scoped` opt-in flag, they are rewritten to that form before the build.
- A finding whose quote sits 4 lines from its cited line, once in the file, is kept with `line_corrected`; a quote present twice outside the window is kept with `line_ambiguous` and its `line` unchanged — never discarded.
- A multi-line quote whose FIRST line sits within ±3 lines of the cited line is kept as cited; one whose first line sits outside the window is corrected or flagged by the same rules.
- **Partial-line quotes:** a partial-line single-line quote and a multi-line quote that starts mid-line are both still accepted (tests for both shapes, in all three consumers).
- **Whole-file fallback:** a re-wrapped quote yields `line_unverified`, not `quote_mismatch`; the four outcomes (`line_corrected`, `line_ambiguous`, `line_unverified`, `quote_mismatch`) each have a test in all three consumers.
- **Acceptance set unchanged:** `line_corrected`, `line_ambiguous` and `line_unverified` findings land in `passed`; `quote_mismatch` is the only Check 3 discard, and it fires only when today's whole-file token match also fails.
- **Render deliverable:** every finding in `passed` carries `line_outcome` — `corrected`, `ambiguous`, `unverified`, or `none` for a quote found within the window — through each of the three consumers' `validate-findings` paths; and `src/commands/review/main.md` (`### 2.4`), `src/commands/audit/main.md` (`### 4.1`) and `src/commands/grill/main.md` (`## PHASE 3`) each carry the sentence telling the orchestrator to list the `corrected` / `ambiguous` / `unverified` rows in its validation summary.
- **Three consumers:** a quote 4 lines off its cited line, once in the file, comes back with `line_corrected` through each consumer's `validate-findings` path — review (`tests/lib/_review/test_brief.py`), audit (`tests/lib/_audit/test_cli.py`) and grill (`tests/lib/_grill/test_cli.py`). Existing `validate_findings` tests stay green; a fixture whose cited line falls outside its quote's window is re-pointed to the quote's line, never deleted, and the Phase 4 record names each one.
- **No counter-quote check:** `git diff` shows no change to `src/devforge/lib/_shared/_verify.py` (D5's Bound 6).
- **D5 (b) wire:** a two-finder fixture citing one line yields `[CROSS-AGENT]` and the severity bump; the two `tests/lib/_review/test_report.py` consensus tests are rewritten to the wired report and are green; grill's two adverts are untouched (D5's Bound 5). **D5 (b) delete:** `grep -rn "CROSS-AGENT" src/commands/review src/devforge/lib/_review src/commands/grill src/devforge/lib/_grill` returns nothing.
- **The preamble difference is preserved:** the review and audit preambles still differ only at the lines where each names its own run, and both carry both D6 sentences verbatim (Trap 5).
- **The grill preamble** carries D6's grill variant verbatim and carries neither the reachability sentence nor the review / audit wording of the count / equivalence sentence (Trap 5).
- No `len()` pin moves: `/devforge:review`'s registry has none (Trap 9).
- Every new function has a test, written and run in the same turn.
- **Targeted first:** `python3 -m pytest tests/lib/_shared tests/lib/_review tests/lib/_audit tests/lib/_grill -q` is green. **Then the full suite:** `python3 -m pytest tests/lib -q` is green.
- `git show --stat` lists only this phase's files and this plan.
- python-reviewer and instruction-reviewer each return SHIP-READY, or every finding is fixed.

#### Phase 4 record

**NOT STARTED.**

### Phase 5 — `/devforge:verify`'s report, ac-verifier and memory rubric (D7, D10, D8, D14, OQ-8)

**Route: python-engineer → python-reviewer for `_verify/_report.py`, `_verify/_verdict.py`, `_verify/_cli.py` and the tests; instruction-author → instruction-reviewer for `src/commands/verify/main.md`, `verify/references/report-format.md`, `src/agents/ac-verifier.md`, `src/agents/design-auditor.md`, `src/commands/specify/main.md` and `src/devforge/memory.md`.**

#### Deliverables

- **`src/devforge/lib/_verify/_report.py`** — D7's per-gate lines in OQ-8's home; **`_verify/_verdict.py`** — D7's reason lines.
- **`src/devforge/lib/_verify/_cli.py`** — `read-ac-config` emits `runtime_scope` (D8).
- **`src/commands/verify/main.md`** — 3.3's brief carries `runtime_scope` and D10's sentence; 5.1 / 5.2 prose; PHASE 7's entry shape (D14). **`verify/references/report-format.md`** — the rendered lines; `:103` reversed for rendered lines only (Trap 7).
- **`src/agents/ac-verifier.md`** — D10's description, `:131` and `## Rules` edits; D8's shared-runtime rule and on-load warning. **`src/agents/design-auditor.md`** — D8's on-load bound.
- **`src/commands/specify/main.md`** Step 4.4 — D8's disposable-record sentence. **`src/devforge/memory.md`** — D14's comments.
- **This plan** — `#### Phase 5 record` below.

#### Verify

- A rendered report carries one line per gate, including `off`, `inconclusive`, `vacuous`, `baseline-failing` and `e2e-clean`, in the home OQ-8's outcome names.
- **No new blocker type:** the blocker-type list in `_verdict.py`'s module docstring (`compute_verdict`'s entry, `:47`–`:51`) is unchanged; each D7 condition adds a reason line and leaves the verdict unchanged. Dead-code `vacuous` renders a gate line and adds no reason line.
- **No e2e duplicate:** for each non-`off` e2e status, `e2e-clean` included, the report carries exactly one `E2E run (…)` reason line — the existing one from `_verdict.py:520`–`:526` — and the e2e gate line renders the status only.
- `read-ac-config` emits `runtime_scope: local` for each loopback host D8's outcome names and `shared` for any other host.
- A mutating AC recorded `UNVERIFIED` on a shared runtime does not block the verdict (Trap 13).
- `src/agents/ac-verifier.md`'s description, `:38` and `:131` agree that the agent does not run the suite, and its `## Rules` carry D10's sentence.
- PHASE 7 and `src/devforge/memory.md` state the same entry shape, and no new `## ` section is added to the template.
- **No new verb:** `tests/lib/_verify/test_preflight.py`'s registry pin is untouched by this phase.
- Every new function has a test, written and run in the same turn.
- **Targeted first:** `python3 -m pytest tests/lib/_verify -q` is green. **Then the full suite:** `python3 -m pytest tests/lib -q` is green.
- `git show --stat` lists only this phase's files and this plan.
- python-reviewer and instruction-reviewer each return SHIP-READY, or every finding is fixed.

#### Phase 5 record

**NOT STARTED.**

### Phase 6 — `/devforge:finalize`'s secret scan (D9)

**Route: python-engineer → python-reviewer for `_finalize/_preflight.py` and its tests; instruction-author → instruction-reviewer for `src/commands/finalize/main.md`.**

#### Deliverables

- **`src/devforge/lib/_finalize/_preflight.py`** — `secret_hits` in `preflight_context`, from D9's pattern set over `specs/<feature>/**`.
- **`src/commands/finalize/main.md`** — the WARN paragraph before the commit step, naming `gitleaks` as the better tool.
- **This plan** — `#### Phase 6 record` below.

#### Verify

- A fixture feature directory holding one hit per pattern kind yields one `secret_hits` row per hit, with `file`, `line` and `kind`; a clean directory yields an empty list.
- The hits are rendered verbatim, and `/devforge:finalize` proceeds: no stop, no blocker, the preflight's exit code unchanged.
- **No new verb:** `tests/lib/_finalize/test_preflight.py:1161`'s registry pin (5) is untouched.
- Every new function has a test, written and run in the same turn.
- **Targeted first:** `python3 -m pytest tests/lib/_finalize -q` is green. **Then the full suite:** `python3 -m pytest tests/lib -q` is green.
- `git show --stat` lists only this phase's files and this plan.
- python-reviewer and instruction-reviewer each return SHIP-READY, or every finding is fixed.

#### Phase 6 record

**NOT STARTED.**

### Phase 7 — Guidance sentences (D11's remaining sites)

**Route: instruction-author → instruction-reviewer, looping until the review is clean.**

#### Deliverables

- D11's sentences in `src/commands/fix/main.md`, `src/commands/breakdown/main.md` (ordering and test strategy), `src/commands/specify/main.md` Step 4.4, `src/commands/plan/main.md` sub-question 9, `src/agents/qa-engineer.md` and `src/agents/qa-reviewer.md`.
- **This plan** — `#### Phase 7 record` below.

#### Verify

- Each D11 sentence, as ratified, greps back verbatim from its site.
- Each sentence passes the sentence-level hallucination check: every command, verb and path it names exists in the tree.
- **Cross-reference sweep:** a grep for each edited heading and quoted phrase finds no other file that restates the old wording.
- `git show --stat` lists only this phase's files and this plan.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 7 record

**NOT STARTED.**

### Phase 8 — Ledgers (D15, D16, D14's amendment, OQ-6)

**Route: instruction-author → instruction-reviewer, looping until the review is clean.** Docs and ledgers only. ⚠ **Ledger edits WAIT until any other session's uncommitted edits to the same files are committed** (Trap 3).

#### Deliverables

- **`CHANGELOG.md`** — lines under `## [Unreleased]`, split across the sub-headings OQ-6's outcome names. They state the evidence class and claim nothing measured.
- **`DEVELOPMENT-STATUS.md`** — `:83` corrected to what the tree does (D15 a), and the bullets for what Phases 1–7 built.
- **`PLAN-STATUS-ARCHIVE.md`** — this plan's index line and entry record.
- **`FINDINGS.md`** — D16 (a) amends entry 11 in place; D16 (b) and (c) add the new entries, numbered after the last entry present at build time; D14's amendment of 128's D9 (b) entry.
- **`115-WRAPPER-INNER-REPO-CBM-VISIBILITY-PLAN.md`** — D15 (b)'s anchoring paragraph.
- **This plan** — its Status line and `#### Phase 8 record` below.

#### Verify

- A `grep -n` for each new `CHANGELOG.md` line's text shows it under `## [Unreleased]`, under the sub-heading OQ-6's outcome names, above the first released version block.
- `grep -n "confirms adding the inner folder" DEVELOPMENT-STATUS.md` returns nothing, and the corrected bullet states that the wrapper substep writes no ignore line.
- `grep -n "^## " FINDINGS.md` shows the new entries last; entry 11 carries the ignored-file arm as an AMENDED line; `git diff FINDINGS.md` adds lines and rewrites nothing outside entry 11 and 128's entry.
- `grep -n "/<inner>/" 115-WRAPPER-INNER-REPO-CBM-VISIBILITY-PLAN.md` finds D15 (b)'s paragraph.
- The identifier grep over the staged diff — run by whoever holds the installation's identifiers — gets no hit.
- `git show --stat` lists only this phase's files and this plan.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 8 record

**NOT STARTED.**

### Consumer e2e — user-driven, NOT run by default

⚠ **The user-driven consumer-install exercise is the repo's deferred final gate; nothing in Phases 1–8 waits on it.** It runs only on the user's direction.

#### Verify

- On a wrapper install whose inner repo carries its own `.claude/` with all of its content tracked or ignored, one task through `/devforge:implement` reaches the `approve` prompt.
- On the same install, one `/devforge:verify` on a feature whose baseline already fails one test reports `regression` on a new failing name.
- The outcome is recorded below with no client identifier.

#### Consumer e2e record

**NOT RUN.**

---

## Non-goals

- **No memory size cap or consolidation step.** 128 D9 (b) records the gap in `FINDINGS.md`; D14 adds an entry shape only.
- **No measurement-first lane, and no harness / baseline / verify directory convention** — the kind of directory a run-gates script would live in. 128 D6 and D7 decline any plan-side or breakdown-side lane and any harness / baseline / verify directory convention; D7's counter-argument RECORDS the installation's measure-first wins without deciding them (R6, K1).
- **No stack reference files and no tooling guidance** (`rtk`, BSD utilities) — D18.
- **No preservation of edited command files in `update.sh`.** Overwrite is the documented policy (F19; D18).
- **No per-file lint, no warning delta and no change to the template's lint line** — the delta is runner-specific, and package-level lint already implies "on changed files" (D12, declined).
- **No PostToolUse type-check hook** (F21); S2's generic half is D13's ordering.
- **No sandbox for verification commands** — 128's Trap 6.
- **No mid-implement spec-amendment path.** D16 (c) records the gap in `FINDINGS.md` and builds nothing.
- **No reorder of PHASE 3 / PHASE 4 in `/devforge:verify`** — D10's declined alternative.
- **No change to `/devforge:configure`'s questions** — the bound 128 F10 states, derived from stub plan 124's measurement (D1's declined alternative, D8's counter-argument, OQ-3).
- **No backport to `main` or the 1.x line.** The handoff asks for the 2.0 line (`## Origin & evidence`).
- **No release cut.** The `CHANGELOG.md` lines land under `## [Unreleased]` (Phase 8).
- **No consumer delivery.** The consumer e2e is user-driven and runs only on the user's direction.
- **No re-verification of the installation's numbers.** They are illustrations (the evidence class).

---

## Context for next session

⚠ **Evidence class: ONE consumer installation; the lessons are that installation's memory as consolidated by a sibling session; NOTHING in them re-verified against the 2.0 tree by the sender; the 2.0 tree VERIFIED here by grep and read on 2026-10-05; NOTHING built and NOTHING measured by this plan. Numbers quoted inside lessons or the handoff ("12 of 52 paths", "6 → 34", "23 of 26 sites", "≈300 → 20 calls", "354 entries / 259 KB") are illustrations from that installation, not benchmarks.** ⚠ All line digits drift — **grep the quoted text, never the digits.**

**The one sentence that governs everything here:** **the lessons are one installation's memory; this plan turns the general ones into mechanisms or sentences and leaves the stack-specific ones with the consumer.**

### Honest bounds

- **One installation, consolidated by a sibling session; nothing re-measured here.** How many other installs hit any of these lessons is unknown.
- **D1's runner table is stack knowledge** and will be wrong for the next runner (D1's counter-argument); its fallback is loud, not silent. A flake that fails only at HEAD still reads as a regression, and the worktree's dependency symlinks stay whole-directory (D1's Bounds 2 and 4).
- **D2's falsification signal is advisory** — a reason line that may be narrated past (D2's counter-argument). Characterization tests pass at the merge-base legitimately, and modified test files are not checked (D2's Bounds). A runner that rejects the file argument, ignores it, or filters on it and matches nothing misreads in one direction or the other, and `output_tail` is the only tell (D2's Bound 5).
- **D3 still flags an untracked, unignored client file that predates the task** — the rule reads the source repo at check time, not at the task's start (D3's Bound 1 and counter-argument); a client ignore line covering a whole artifact path hides what the agent writes under it (D3's Bound 4).
- **D4's hook guards only commits made outside `/devforge:implement`**, and a walk-up can reach another install's `.devforge` unless bounded (D4's Bound 2 and counter-argument).
- **D5 (a) is a heuristic window in the SHARED validator**: it rejects nothing the old check accepted, but its flags change nothing unless every consumer renders them, and a correction can land on a different site that carries the same text — a confident mis-citation (D5's counter-argument); `/devforge:audit` and `/devforge:grill` inherit the rule (grill will see more `line_corrected` rows), and consensus groups on the exact line (D5's Bounds 1 and 4). Flagged findings (`line_ambiguous`, `line_unverified`) carry a line nothing verified (D5's Bound 7). Refuter counter-quotes stay unchecked, and under wire grill's two `[CROSS-AGENT]` adverts stay dangling (D5's Bounds 6 and 5).
- **D8's host rule is coarse**: navigation can still fire an on-load mutation, and a container-hosted dev server loses mutating verification (D8's Bounds and counter-argument).
- **D9's secret scan is WARN-only and regex-based** — noisy, blind to structured secrets, and near-zero protection when narrated past (D9's Bounds and counter-argument).
- **D10, D11 and D14 are prose**, and prose rules are unmechanical (D11's counter-argument). **D12 changes nothing:** a consumer reading "on changed files" expects per-file evidence the report never shows (D12's counter-argument).
- **The ignored-file blindness D16 (a) records is inferred from git behaviour, not run.**
- **131 builds after 112–130, and 128 edits the same files first** (D17) — every anchor above will have drifted; re-anchor by the quoted text.

### Traps

**Trap 1 — line digits.** Every anchor here was read on 2026-10-05, and plan 128 builds first and edits the same files. Re-anchor by searching the quoted text before every edit.

**Trap 2 — client identifiers.** This file is tracked in a public repo. Describe the installation as "one consumer installation (wrapper mode, running the 1.x command layout)" and the sender as "a sibling session", every time, in every phase's commit, record and ledger line.

**Trap 3 — concurrent sessions and explicit-path commits.** Other sessions build in this checkout. Commit by explicit path, check `git show --stat` after every commit, and hold Phase 8's ledger edits until other sessions' uncommitted edits to those files are committed.

**Trap 4 — the existing isolation tests KEEP their meaning; the new cases need a git repository.** `test_dot_claude_dir_found` (an EMPTY `.claude`) and `test_claude_md_found` (an untracked, unignored `CLAUDE.md`) stay pollution under D3's untracked-content rule; their fixture is a plain `tempfile.mkdtemp()` directory, not a git repository, so after the change they exercise the fallback existence check. Do not rewrite them and delete none of them; the tracked and all-ignored cases are NEW tests in a temp git repository.

**Trap 5 — three refutation preambles, two sentence sets.** The review and audit preambles are identical except at `:3` and `:6`: both get both D6 sentences, and that difference is kept. The grill preamble (`src/commands/grill/references/refutation-preamble.md`) is design-level: it gets only D6's grill variant of the count / equivalence sentence — without the code-shaped words "a reach claim" and "multi-line imports" — and never the reachability sentence.

**Trap 6 — `_consensus` groups on the EXACT line** (`_consensus.py:22`). After D5 (a)'s correction, two citations of one defect merge only when both land on the same line.

**Trap 7 — `report-format.md:103` is reversed for rendered lines only.** A non-violation status gains a rendered line under D7 and still adds no blocker.

**Trap 8 — `_run_test_cmd` returns a TAIL** (`_TAIL_LINES = 50`). D1 needs the full output, byte-capped. The same function's `(1, …)` collapse of its three exception arms (`_regression.py:322`–`:327`) is, with the exit 126 and 127 mapping, the second change Phase 1 makes to it (one not-run outcome for every cause); a build that captures the full output but keeps the collapse leaves D2's `not_run` and D1's not-run `inconclusive` reachable only through exit 126 or 127: a timeout, an `OSError` or any other exception reads as a failed run — `baseline-failing` at the merge-base, `regression` at HEAD on a green baseline.

**Trap 9 — registry pins.** `tests/lib/_verify/test_preflight.py:728` asserts 16 today, and 128 moves it to 17. D5 (b) adds a REVIEW verb, and `/devforge:review`'s registry has no `len()` pin, so nothing there moves.

**Trap 10 — `rtk` display output is lossy.** A display can drop or truncate lines. Read exact test output via `rtk proxy` plus a file redirect, then read the file.

**Trap 11 — `## [Unreleased]` sub-headings.** They carried `### Changed` and `### Fixed` on 2026-10-05. Re-verify them LIVE at build time; never edit a released block.

**Trap 12 — D4's walk-up must not cross into another install.** Bound it as D4's outcome names, and test it with nested installs.

**Trap 13 — D8's `UNVERIFIED` must not become a failure.** `compute_verdict` counts only `FAIL` / `PARTIAL` as AC failures (`_verdict.py:57`, `:149`–`:152`); keep it that way, so a shared-runtime `UNVERIFIED` never blocks.

**Trap 14 — `DEVELOPMENT-STATUS.md:83` is FALSE today.** Nothing writes the inner-repo ignore line (F18); never cite that line as a mechanism.

### File anchors

**EDIT targets — a phase of this plan writes each of these:**

- **Phase 1:** `src/devforge/lib/_verify/_regression.py` (`:3`, `:101`, `:107`, `:113`, `:168`, `:267`, `:304`, `:308`, `:321`, `:322`–`:327`, `:435`–`:486` — including `:436`, the baseline status mapping, and the verdict block `:448`–`:486`); `src/devforge/lib/_verify/_verdict.py` (D2's reason line); `src/commands/verify/main.md` `### 4.3` (`:259`); `src/commands/verify/references/report-format.md` (`:98`–`:103`); tests under `tests/lib/_verify/` and fixtures under `tests/lib/fixtures/`.
- **Phase 2:** `src/devforge/lib/_implement/_cmds_verify.py` (`:26`, the docstring's order; `:27`, `:99`, `:187`–`:197`, `:514`–`:529`, `:538` `cmd_verify_touched`, `:601`–`:624` — including the order comment at `:619`–`:622`; `:659`, `:673`); `src/commands/implement/main.md` (`:182`, `:187`); `src/commands/fix/main.md` (`:346`, the order clause; `:351`, the `isolation_failure` remedy); `src/commands/verify/main.md:243` (PHASE 4.1's order clause); `src/CLAUDE.md:175` (scope-aware verification step 4); `src/commands/implement/references/agent-brief.md:18`; `tests/lib/_implement/test_cmds_verify.py` (new temp-git-repo isolation tests; `:1079` and `:1085` stay unchanged).
- **Phase 3:** `src/commands/constitute/main.md` `### Phase 6.4` (`:616`, the two install lines `:629`–`:630`); `src/git-hooks/pre-commit-forcing-functions.sh` (`:19`, `:25`, `:32`–`:34`); `scripts/post-update-checks.sh` (`:83`–`:118`); `src/devforge/lib/_constitute/_cli.py` (the new `verify-hook` verb; `src/devforge/lib/constitute_helper.py` is the entry point); `tests/lib/test_constitute_helper.py` (its tests).
- **Phase 4:** `src/devforge/lib/_shared/_validate.py` (`:71` `_normalize_whitespace`, `:119` `validate_findings`, `:210`, `:213`–`:219`); `src/devforge/lib/_review/_cli.py` (the registry); `src/devforge/lib/_review/_report.py:134`; `src/commands/review/main.md` (`### 2.4` at `:191`, the `validate-findings` call at `:200`; `### 2.6` at `:248`); `src/commands/audit/main.md` (`### 4.1` at `:312`, the `validate-findings` calls at `:321` and `:334`; the render sentence); `src/commands/grill/main.md` (`## PHASE 3` at `:190`, the `validate-findings` call at `:203`; the render sentence); `src/commands/review/references/report-format.md:53`; `src/devforge/lib/_grill/_report.py:185` and `src/commands/grill/references/report-format.md:59` (delete arm only); `src/commands/review/references/refutation-preamble.md` and `src/commands/audit/references/refutation-preamble.md` (`:10`, `:27`–`:28`, `:47`); `src/commands/grill/references/refutation-preamble.md` (`:11`–`:13`; D6's grill variant only); tests — `tests/lib/_shared/test_validate.py`, `tests/lib/_review/test_brief.py`, `tests/lib/_audit/test_cli.py`, `tests/lib/_grill/test_cli.py`, `tests/lib/_grill/test_merge.py`, and `tests/lib/_review/test_report.py` (`:421`–`:424`, `:605`–`:608`; wire arm only).
- **Phase 5:** `src/devforge/lib/_verify/_report.py` (`:101` `render_report`, `:358` `render_inline_summary`); `src/devforge/lib/_verify/_verdict.py` (`:146`, `:157`, `:484`, `:521`); `src/devforge/lib/_verify/_cli.py` (`read-ac-config`: `:213`, `:1161`, `:1377`); `src/commands/verify/main.md` (`:193`, 3.3 at `:199`–`:212`, `### 5.1` `:329`, `### 5.2` `:338`, PHASE 7 at `:372`–`:390`); `src/commands/verify/references/report-format.md` (`## Code Quality` `:42`, `:103`); `src/agents/ac-verifier.md` (`:3`, `:38`, `:60`–`:71`, `## Rules` `:124`, `:131`); `src/agents/design-auditor.md` (`:34`, `:37`, `:49`); `src/commands/specify/main.md` Step 4.4 (`:661`); `src/devforge/memory.md` (`:1`–`:13`).
- **Phase 6:** `src/devforge/lib/_finalize/_preflight.py:214`; `src/commands/finalize/main.md` (the commit step).
- **Phase 7:** `src/commands/fix/main.md:332`; `src/commands/breakdown/main.md` (`:262`, `:405`); `src/commands/specify/main.md:663`; `src/commands/plan/main.md:437`; `src/agents/qa-engineer.md:45`; `src/agents/qa-reviewer.md:27`.
- **Phase 8:** `CHANGELOG.md` (`:8`–`:18`); `DEVELOPMENT-STATUS.md:83`; `PLAN-STATUS-ARCHIVE.md`; `FINDINGS.md` (`## 11.`, `## 12.`, and 128's D9 (b) entry once it lands); `115-WRAPPER-INNER-REPO-CBM-VISIBILITY-PLAN.md`.
- **This plan** — every phase's record and, at Phase 8, the Status line.

**READ-ONLY anchors — no phase of this plan writes any of these:**

- `128-AC-VERIFICATION-COMMAND-GATE-PLAN.md` (D2–D9, F3–F10, Trap 6) — the overlap this plan cites; its *"No `src/CLAUDE.md` edit"* non-goal (`:388`), which D13 distinguishes; F10's cost bound (`:70`); D5's counter-argument (`:128`), which D2's coordination cites; D9's heading (`:148`), D9 (a) (`:150`) and the *"No memory template or PHASE 7 rubric change"* non-goal (`:385`), which D14 departs from on the entry shape only.
- `124-PIPELINE-COST-REDUCTION-PLAN.md` (a stub) — the measurement the cost bound derives from; the bound itself is stated by 128 F10 (`128-AC-VERIFICATION-COMMAND-GATE-PLAN.md:70`).
- `125-VERIFY-FILE-BUGS-IMPORT-PLAN.md` — the close-record shape, and its D5 queue jump (D17's counter-argument); `98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md` — its D1 pick-or-delegation distinction.
- `97-WRAPPER-MODE-FRAMEWORK-MENTION-GUARD-PLAN.md` — the content-level guard (D4's Bound 1).
- `111-WIP-MARKER-CONTRACT-PLAN.md` (`3fa3b10`) — the marker D3's alternative (b) would touch.
- `87-ARTIFACT-LANGUAGE-GUARD-PLAN.md` fact 3 — when `.claude/settings.local.json` is ignored.
- `src/devforge/lib/_shared/_consensus.py` (`:22`, `:31`–`:33`, `:114`, `:120`–`:126`) — D5 (b) calls it and edits nothing in it.
- `src/devforge/lib/_shared/_verify.py` (`apply_verdicts`, `:564`; its docstring, `:590`) — D5's Bound 6: refuter counter-quotes stay unchecked, and no phase edits it.
- The three `validate_findings` callers — `src/devforge/lib/_review/_cli.py:309`, `src/devforge/lib/_audit/_cli.py:653`, `src/devforge/lib/_grill/_cli.py:488` — inherit D5 (a); no phase edits these call lines; `src/devforge/lib/_audit/_merge.py` and `12-AUDIT-MULTI-PASS-UNION-PLAN.md` — audit's multi-pass path, which replaces consensus (D5's parity qualifier).
- `src/devforge/lib/_implement/_cmds_capture.py` (`:6`–`:11`) — D16 (a) records its ignored-file arm; no phase changes it.
- `src/commands/implement/main.md` (`:68`–`:69`, `:108`, `:116`, `:131`, `:165`, `:179`, `:184`, `:331`) — OQ-1's evidence and F4 / F8.
- `src/devforge/lib/breakdown_helper.py:1007`; `src/devforge/storage-rules.md:241`; `src/CLAUDE.md:221` (Always-rule 8) — the lint lines D12 declines to change; and the tests that pin the template line: `tests/lib/test_breakdown_helper.py` (`:1837`, `:1854`, `:1875`, `:1949`, `:1978`), `tests/lib/_implement/test_handoff_reader.py:188`, `tests/lib/_implement/test_cmds_resolve.py:180`.
- `src/devforge/lib/_verify/_dead_code.py` (`:57`–`:58`, `:80`, `:88`–`:91`, `:193`–`:195`); `src/devforge/lib/_verify/_e2e.py` (`:93`–`:95`, `:154`, `:301`–`:305`, `:321`–`:323`).
- `src/CLAUDE.md:55`–`:61` and `:63`–`:66` — the workflow list's WIP-commit clauses D9's bound cites (`:62`, `/devforge:implement`, carries none).
- `src/devforge/lib/_shared/memory.py` (`:131`–`:132`, `:147`, `:327`, and `:393`–`:395`, the newest-last cut rule D14 relies on); `src/manifest.json` (`:29`, `:36`–`:47`); `update.sh` (`:1093`–`:1096`); `install.sh` (`:309`, `:339`–`:345`).
- `src/commands/configure/main.md` (`:17`, `:89`, `:129`, `:145`–`:146`, `:453`); `src/devforge/lib/_configure/_cmds_read.py` (`:207`, `:214`, `:218`).
- `src/devforge/lib/_generate_docs/_validators_shared.py` (`:101`–`:106`); `src/devforge/lib/_generate_docs/_validators_file_doc.py:185`.
- `src/constitution.md` (`:96`, `:100`); `src/commands/research/main.md` (`:856`–`:872`); `src/devforge/lib/_specify/_cmds_phase4_verify.py` (`:123`–`:125`); `src/commands/specify/main.md` (`:208`, `:667`, `:1031`).
- `src/commands/init-forge/main.md` (`:45`–`:82`); `src/files/devforge.gitignore`.
- `src/commands/breakdown/main.md` (`:166`, `:492`, `:710`); `src/commands/finalize/main.md` (`:154`, `:282`); `src/commands/constitute/main.md:274`.
- `tests/lib/_verify/test_preflight.py:728`; `tests/lib/_finalize/test_preflight.py:1161` — pins no phase moves.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation.
2. **Check `### Phase 0 close record` FIRST.** While it reads OPEN, nothing is ratified and no build phase may start.
3. **Check the queue position before any build.** Plans 112–130 sit ahead of 131, and 128 edits the same files (D17); a build starts only when they are done or D17's outcome ratifies a jump.
4. **See what landed:** `git log --oneline -- src/devforge/lib/_verify src/devforge/lib/_implement src/devforge/lib/_shared src/devforge/lib/_review src/devforge/lib/_finalize src/devforge/lib/_constitute src/devforge/lib/constitute_helper.py src/devforge/lib/_grill src/devforge/memory.md src/commands/verify src/commands/implement src/commands/review src/commands/constitute src/commands/fix src/commands/audit src/commands/grill src/commands/specify src/commands/breakdown src/commands/plan src/commands/finalize src/agents src/CLAUDE.md src/git-hooks scripts/post-update-checks.sh`.
5. **Re-verify F1–F22 by grepping the quoted text, never the digits.** F1's `baseline-failing` branch, F8's `ISOLATION_ARTIFACTS` tuple, F9's two install lines, F10's 2.6 without a consensus call and F18's `DEVELOPMENT-STATUS.md:83` claim are the checks that each gap is still open; a change in any of them means some other change has touched that gap.
6. **Route every edit through the house flow:** python-engineer → python-reviewer for every Python edit; instruction-author → instruction-reviewer for every markdown edit; each loop runs until its review is clean. **Commit by explicit path, never `git add -A`.**
7. **Keep the evidence class** (stated at the top of `## Origin & evidence` and of `## Context for next session`) **and the public-repo rule** (`## Origin & evidence`, Trap 2) **attached** to every summary of this plan.
