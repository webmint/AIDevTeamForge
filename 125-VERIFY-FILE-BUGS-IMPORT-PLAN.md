# 125 — Verify File-Bugs Import Plan

**Created**: 2026-10-02
**Status**: **Phase 0 CLOSED 2026-10-02 by blanket directive — D1, D2, D3, D4, D5, D6 and OQ-1 are each ratified as recommended (`### Phase 0 close record`).** **Phase 1 BUILT 2026-10-02, committed with its record (`#### Phase 1 record`). Phase 2 (built, under its full-suite Verify) is committed next, then Phase 3. Phase 4 waits on D6's frozen-install confirmation, which has NOT been given.** ⚠ **Numbered 125 because a glob of `1[0-2][0-9]-*.md` at the repo root on 2026-10-02 returns 100–102 and 104–124 and no 125. The gap at 103 is vacated and must not be reused.**

`verify_helper file-bugs` — the verb `/devforge:verify` PHASE 9 calls when the user elects to file bugs on a NEEDS WORK verdict — **raises `ImportError: attempted relative import beyond top-level package` on every call.** *(added 2026-10-02 — Phase 1: the verb is fixed in this tree; this paragraph describes the pre-fix state, and installs not yet carrying the fix still raise — see `#### Phase 1 record`)* **The cause is one line:** `cmd_file_bugs` imports `from .._shared.bug_file import file_bugs`, and the launcher loads `_verify` as a TOP-LEVEL package, so `..` has no parent package to resolve against (F1, F2). **The fix is one line:** the absolute form every other importer of `_shared.bug_file` uses, and the form the same file already uses for `_shared.feature_scope` (F3, D1). **The suite never saw it because the import is function-local and no test calls the verb** (F6). D2 closes that gap for this verb; D3 proposes a guard for the whole class; D4 records, and does not fix, a second defect the same consumer run exposed (F11).

---

## Origin & evidence

⚠ **Evidence class, to be repeated in every summary of this plan: ONE observed consumer incident; the mechanism REPRODUCED in this tree; the fix verified in a SCRATCH COPY only; nothing measured.** *(added 2026-10-02 — Phase 1: that class held until Phase 1; as of Phase 1 the fix is verified in this tree as well — see `#### Phase 1 record` — so every summary from Phase 1 on repeats it as "ONE observed consumer incident; the mechanism REPRODUCED in this tree; the fix verified in a SCRATCH COPY, then in this tree by Phase 1; nothing measured.")* A consumer install's `/devforge:verify` run reached a NEEDS WORK verdict, the user elected to file bugs, the `file-bugs` call raised the F1 ImportError, and no bug file was written. The incident's artifacts are held outside this repo; the maintainer knows which install it was. **How many other installs have hit it is unknown** — the verb runs only on a NEEDS WORK verdict with an elected filing, and nothing reports a crash back to this repo.

This repo is public. **This plan names no client, no install, no project or workspace name, no ticket id, no package name and no path outside this repo**, and no phase of it may introduce one. The issue the consumer tried to file is described here only as one issue with severity `Warning` and `ac_ref` `N/A`.

### Verified structure (2026-10-02)

⚠ **Line digits drift — grep the quoted text, never the digits.**

**F1 — The broken line.** `src/devforge/lib/_verify/_cli.py:1080` reads `from .._shared.bug_file import file_bugs`. It is the first statement of `cmd_file_bugs` (`def` at `:1069`) after its docstring, so it runs before the argument checks at `:1087`–`:1092` — **every call of the verb reaches it, whatever its arguments.** `main` (`:1801`–`:1814`) dispatches `args.func(args)` without a `try`, so the ImportError escapes as a traceback. *(added 2026-10-02 — Phase 1: the tree's line is now the absolute form; see `#### Phase 1 record`)*

**F2 — The loader topology.** `src/devforge/lib/verify_helper.py:16`–`:18` inserts the launcher's own directory onto `sys.path` — `src/devforge/lib/` in this repo, `.devforge/lib/` in an install, which is where `src/commands/verify/main.md:419` calls it through the POSIX shim (`src/devforge/lib/verify_helper:16`–`:19` execs `verify_helper.py`) — and `:20` imports `from _verify._cli import main` by its absolute top-level name. `src/devforge/lib/` carries no `__init__.py`. **`_verify` is therefore a top-level package under every invocation of the launcher, and a level-2 relative import in a module directly inside it climbs above it.** `04-PR-REVIEW-PLAN.md:126` (*"Import topology note"*) records the same topology and this exact ImportError for `research_helper`.

**F3 — The convention every other site follows.** `grep -rn "_shared.bug_file import" src/` returns four sites, and the other three are absolute: `src/devforge/lib/_report_bug/_cli.py:82` (`from _shared.bug_file import file_bugs`, function-local), `src/devforge/lib/_fix/_cli.py:302` (`from _shared.bug_file import close_bug`, function-local) and `src/devforge/lib/_shared/ticket_file.py:106` (`from _shared.bug_file import scan_highest_number, slugify`, module-level). ⚠ **The nearest precedent is in the broken file itself:** `_verify/_cli.py:159` imports `from _shared.feature_scope import resolve_feature_scope` — absolute and function-local. Every other handler-level import there except `:159` (`:55` through `:1058`) is a level-1 sibling import, which F2's topology permits; `:159` is the only non-relative indented `from` import in that range. `install.sh:142`–`:144` states the convention in a comment (*"refactored helpers import shared infra"*, `:142`).

**F4 — The consequence.** `src/commands/verify/main.md`'s `## PHASE 9` (`:408`) offers filing on NEEDS WORK only (`:414`) and makes the `file-bugs` call at `:419`; `:441` instructs *"On a non-zero exit, copy the helper's stderr VERBATIM and end the turn."* **With F1 in place, every elected filing in every install whose `.devforge/lib/_verify/_cli.py` carries that line stops there with no `bugs/NNN-*.md` written.** `verification.md` already exists by then (written in PHASE 5.2, per `:453`), so the verdict is not lost. What happens to `## Cleanup` after the failure is F11.

**F5 — Origin: a plan prescribed the broken line.** `27-REPORT-BUG-COMMAND-PLAN.md:28`, in plan 27's Phase 0, instructs: *"re-point `_verify/_cli.py` import (`from ._bugs import file_bugs` → `from .._shared.bug_file import file_bugs`)"*. Commit `027bdd4` (2026-06-19, *"refactor(bugs): move file_bugs to _shared/bug_file.py + source param"*) landed it. The line it replaced, `from ._bugs import file_bugs`, was a level-1 sibling import and valid under F2. The verb itself shipped with plan 22's command in `a8fdcf9` (2026-06-17, *"feat(verify): live AC + mechanical + verdict command (plan 22)"*). Both subjects and dates are in this checkout's git history, verified 2026-10-02: `git show -s --format='%h %ad %s' --date=short 027bdd4 a8fdcf9` returns `027bdd4 2026-06-19 refactor(bugs): move file_bugs to _shared/bug_file.py + source param` and `a8fdcf9 2026-06-17 feat(verify): live AC + mechanical + verdict command (plan 22)`; re-derive with that command. ⚠ **Plan 27's own Verify (`:31`) required `tests/lib/_verify` green — and it was green, because nothing in it calls the verb (F6).**

**F6 — Why no test caught it.** Three facts, together sufficient. **(a)** The import is function-local, so loading `_verify._cli` succeeds and every test that imports `main` stays green. **(b)** `tests/lib/_verify/test_bugs.py:65` imports `from _shared.bug_file import file_bugs, slugify, scan_highest_number` directly, and its module docstring (`:1`) reads *"Tests for src/devforge/lib/_shared/bug_file.py (relocated from _verify/_bugs.py)"* — **it tests the writer, never the verb**, and its location invites the opposite assumption. **(c)** `tests/lib/_verify/test_preflight.py:730`, `test_registry_verb_names`, asserts that `"file-bugs"` (`:748`) is registered, and `grep -rn '"file-bugs"' tests/` returns only that line. **A registered name is not a call.**

**F7 — Reproduced in this tree.** `python3 src/devforge/lib/verify_helper.py file-bugs --issues <issues.json> --bugs-dir <dir> --date 2026-10-02` raises the F1 ImportError. Calling `main(["file-bugs", "--issues", …, "--bugs-dir", …, "--date", "2026-10-02"])` IN-PROCESS with `src/devforge/lib` on `sys.path` raises the same error — **because the tests load `_verify` as a top-level package exactly as the launcher does** (e.g. `tests/lib/_verify/test_scope.py:27`–`:33`). That is why D2 needs no subprocess harness. *(added 2026-10-02 — Phase 1: both calls now succeed in this tree; the RED was reproduced before the fix — see `#### Phase 1 record`)*

**F8 — The fix, verified in a SCRATCH COPY only.** In a scratch copy of `lib/`, with only `:1080` changed to `from _shared.bug_file import file_bugs`, the consumer's real issue payload ran through the launcher: exit 0, one `bugs/001-*.md` written in the storage-rules format with `**Source**: verify`. **So the payload was valid and that one line is the whole runtime fix.** ⚠ **The tree's `:1080` is still broken on 2026-10-02; Phase 1's Verify, not this record, proves the fix in the tree.** *(added 2026-10-02 — Phase 1: Phase 1 fixed that line later the same day, and its Verify proved the fix in the tree — see `#### Phase 1 record`)*

**F9 — The class: one broken site in fourteen hits.** `grep -rn 'from \.\.' src/devforge/lib` returns 14 hits on 2026-10-02. **`_verify/_cli.py:1080` is the ONE broken site** — directory depth 1 below `lib/`, relative level 2. **12 are healthy imports at directory depth 2 or 3**, where `..` resolves inside the top-level package: `_generate_docs/_doc_setters/_cmds_package.py:19`, `_generate_docs/_doc_setters/_skeletons.py:16`, `_constitute/_forcing_functions/_setters.py:46`, `_constitute/_forcing_functions/_cli.py:141`, and 8 under `_constitute/_forcing_functions/{_any_leak,_cross_layer,_magic_enum,_design_tokens}/{_cmd,_scanner}.py`. `_design/_source.py:49` is a comment, not an import.

**F10 — The consumer install's copy matches the tree.** Verified 2026-10-02: the consumer install's `.devforge/lib/_verify/` (whole directory, `__pycache__` excluded; `diff -rq`) and `.devforge/lib/_shared/bug_file.py` (`diff -q`) are byte-identical to this working tree's `src/devforge/lib/` copies; `git log --oneline -3 -- src/devforge/lib/_verify/` shows `b609b21` (2026-09-19, plan 97 Phase 2) as the latest commit touching `_verify/`. ⚠ **This is a 2026-10-02 snapshot; D6 step 2 re-checks it at delivery time.**

**F11 — A second, independent defect in the same run.** Followed as written, `:441` ends the turn before `## Cleanup` (`:445`), so Cleanup's state flip and WIP commit do not run after a failed filing. The consumer's orchestrator instead issued `file-bugs`, `check-status-and-flip --to phase9 --status complete` (`verify/main.md:450`), `artifact_helper commit-artifacts` (`:459`) and `rm -rf "$WORKDIR"` (`:468`) in ONE Bash call, and the later commands ran after `file-bugs` failed. **`:441`'s end-the-turn rule had no point at which to fire**, so Cleanup ran after the failed filing: state was marked complete, the WIP commit landed and the scratch `issues.json` was deleted, although no bug was filed. The report and the commit are correct; the issue text survived only in the consumer session's context. **This is not F1's defect, and D4 keeps it out of this plan's build.**

---

## Phase 0 — ratification

Nothing below is ratified. *(added 2026-10-02 — Phase 0 close: that sentence held until the close; every item below is now ratified as recommended, under a blanket directive, and its outcome is in `### Phase 0 close record` at the end of this section — nothing below is deleted, shortened or answered away by the close)* Each item states the question, its options, a recommendation, what it costs, and the strongest counter-argument, **recorded honestly rather than answered away**.

### D1 — The fix

- **Option A — the absolute form, kept function-local:** `from _shared.bug_file import file_bugs`, on the same line inside `cmd_file_bugs`. It matches the in-file precedent at `:159` and both other `_cli.py` importers of `_shared.bug_file`, which also import lazily (F3).
- **Option B — hoist the absolute import to module top**, so loading `_verify._cli` fails loudly if it ever breaks again. Every handler in this file imports lazily (`:55`–`:1080`), and a top-level import makes every verb, not only `file-bugs`, depend on `_shared/bug_file.py` at load time.

**RECOMMEND A**, for consistency with the surrounding lazy-import idiom; D3 covers the detection gap B would cover. **Cost:** one line.
**Counter-argument, recorded:** **a lazy import is exactly what hid this bug for months**, and B would have made it fail in every `_verify` test on the day it landed. A without D3 keeps that blind spot open for the next lazy import.

### D2 — A regression test that CALLS the verb

**Proposal:** in-process test(s) in `tests/lib/_verify/test_bugs.py` that call `_verify._cli.main(["file-bugs", "--issues", <path>, "--bugs-dir", <dir>, "--date", "2026-10-02"])` through a `_capture` helper of the shape at `tests/lib/_verify/test_scope.py:100` and `tests/lib/_fix/test_close_bug.py:58`, and assert: return code 0; exactly one file in `--bugs-dir`; stdout parses as a JSON array equal to the list of written paths; that file contains `**Source**: verify`. The issue fixture is synthetic — the existing `_issue()` builder at `test_bugs.py:73` — never the consumer's payload.
**Why in-process suffices:** the file already puts `src/devforge/lib` on `sys.path` (`test_bugs.py:59`–`:63`), so `_verify` loads top-level exactly as under the launcher, and F7 shows the in-process call reproduces the launcher's failure.
**Red-before-green is MANDATORY:** the new test runs against the unfixed `:1080` first and must ERROR with `ImportError: attempted relative import beyond top-level package` (`main` does not catch it, F1; `_capture` catches only `SystemExit`). A red for any other reason does not count (Trap 7).
**Alternative considered:** a separate CLI-only test file, mirroring `test_close_bug.py`'s split (its docstring: *"this file covers the CLI surface only"*). Not recommended: `test_bugs.py` is the `_verify` test file already named for bug filing, and the same change updates its `Coverage:` docstring block (`:3`–`:48`) so that block stops implying the writer is all it covers.
**RECOMMEND as proposed.** **Cost:** one helper and one to three tests in one file.
**Counter-argument, recorded:** **an in-process test reproduces the launcher only while the test's `sys.path` matches the launcher's.** If `lib/` ever became an importable package in the test process, the in-process call would stop reproducing F1 while a subprocess call would not. D3's guard does not depend on `sys.path` at all.

### D3 — A class-wide guard (scope expansion — the maintainer decides)

**Proposal:** a test that parses every `.py` under `src/devforge/lib/` with `ast` and fails on any `ImportFrom` whose `level` exceeds the file's directory depth below `lib/`. Depth: a file directly in `lib/` is 0; `lib/_verify/_cli.py` is 1; `lib/_constitute/_forcing_functions/_setters.py` is 2. The rule holds unchanged for `__init__.py`, whose package is its own directory. The guard reports EVERY offending `file:line` in one failure message; a file that fails to parse fails the guard, named — it is never skipped; `__pycache__` is excluded.
**Pro:** it catches a lazy import no module-load test sees — the exact property that let F1 live from 2026-06-19 until a consumer hit it. It reads the live `src/` tree the way `tests/lib/test_agent_reachability.py` and `tests/lib/test_memory_lane.py` do, and AST-scanning tests have precedent (`tests/lib/_review/test_report.py:840`–`:868` walks `ast.ImportFrom` nodes; `tests/lib/_specify/test_verify_change_kind_coherence.py:284` parses a source file with `ast` and walks its `Name` / `Attribute` nodes).
**Con:** scope beyond the reported bug. **Without it, D2 protects exactly one verb.**
**Location:** `tests/lib/test_relative_import_depth.py`, a new file; the name is the maintainer's to change at ratification *(ratified unrenamed 2026-10-02 — see `### Phase 0 close record`)*. **Mutation check, mandatory:** the guard fails with `:1080` in its broken form, naming `_verify/_cli.py`, and passes after D1.
**RECOMMEND include.** **Cost:** one new test file.

### D4 — The F11 observation: record it, do not fix it here

- **Option A — a new numbered entry in `FINDINGS.md`** (entries run `## 1.` to `## 7.` on 2026-10-02), in entry 7's shape, outside this plan's build.
- **Option B — tighten `src/commands/verify/main.md`'s PHASE 9 / Cleanup wording in this plan.** The phrase *"VERBATIM and end the turn"* appears in 11 files under `src/commands/` (grep, 2026-10-02), so whether an orchestrator may chain a stop-on-failure call with later steps is a cross-command orchestration question, not this bug.

**RECOMMEND A.** **Cost:** one `FINDINGS.md` entry. **Impact being recorded rather than fixed:** low — the report and commit are correct; the false part is a `complete` state with no bug filed.
**Counter-argument, recorded:** **a `FINDINGS.md` entry has no owner**, and F11 is a real way for `/devforge:verify` to record a finished run that silently skipped the user's elected filing. Recording it defers that defect; it does not bound it.

### D5 — Queue position

Plans execute in numeric order, and every lower-numbered open plan sits ahead of this one (the maintainer's working rule, restated in `111-WIP-MARKER-CONTRACT-PLAN.md`'s `### Honest bounds`). Plan 107's build closed on 2026-10-01 (`PLAN-STATUS-ARCHIVE.md:97`); the maintainer names 108 as next in line.
**RECOMMEND that 125 build ahead of the queue.** A shipped verb has been broken in every install carrying F1's line since `027bdd4` (2026-06-19), and no plan file numbered 100–124 mentions `_verify/_cli.py`, `_verify._cli`, `file-bugs`, `file_bugs` or `bug_file` (grep, 2026-10-02), so there is no overlap to collide with. **Cost:** one exception to the ordering rule.
**Counter-argument, recorded:** **the ordering rule exists so plans never build on each other's half-landed state**, and every exception makes the next one cheaper to argue. **The maintainer decides.**

### D6 — Delivering the fix to the consumer that surfaced it (user-driven, outside the repo)

**Proposal — surgical, never a full install:**
1. **Precondition:** the maintainer confirms that install is NOT the frozen benchmark install. Without that confirmation Phase 4 does not run.
2. **Re-check at delivery time** — F10 matched on 2026-10-02, and the consumer can change between then and delivery. `diff` the consumer's `.devforge/lib/_verify/_cli.py` against the fixed `src/devforge/lib/_verify/_cli.py`: the only delta must be the import line. Then `diff` the consumer's `.devforge/lib/_shared/bug_file.py` against `src/devforge/lib/_shared/bug_file.py`: they must be identical, because the fixed import resolves to the install's own copy. **Any other delta stops the delivery, and the delta is recorded.**
3. Copy that one file over the consumer's copy, then `rm -rf` the consumer's `.devforge/lib/_verify/__pycache__`.
4. In the consumer session, recompose the issue payload — its scratch `issues.json` was deleted by the chained Cleanup (F11) — write it to scratch, and re-run ONLY the `file-bugs` call in `verify/main.md:419`'s form. **Do not re-run `/devforge:verify`:** its report and WIP commit already exist. Per `verify/main.md:462` a PHASE 9 bug file is never part of `/devforge:verify`'s commit, so this delivery commits nothing.

**Do NOT run `install.sh` or `update.sh` against that install:** they deliver from the whole working tree, including every change under `CHANGELOG.md`'s `## [Unreleased]` (`:8`), not this one line.
**RECOMMEND as proposed.** **Cost:** one file copy and one helper call, run by the user.
**Counter-argument, recorded:** **a hand-patched install matches no release** until its next update, so a later report from it is harder to attribute to a version.

### OQ-1 — Which `CHANGELOG.md` sub-heading the entry goes under

`## [Unreleased]` has only `### Changed` today (`:10`). In the released blocks every `- fix(` entry but one sits under `### Fixed` — e.g. `[2.0.12]` (`:32`–`:33`) and `[2.0.11]` (`:40`–`:43`); the one exception is `:96`, under `[2.0.8]`'s `### Changed` (`:94`).
**RECOMMEND `### Fixed`**, added under `## [Unreleased]` after `### Changed` when still absent at build time, matching the order in `[2.0.12]` and `[2.0.11]`. **Alternative:** `### Changed`, the only sub-heading present, with `:96` as its single precedent.
⚠ **Re-verify LIVE at build time, and never edit a released version block.**

### Phase 0 close record

**CLOSED 2026-10-02 by blanket directive.** **D1, D2, D3, D4, D5, D6 and OQ-1 are each ratified as recommended, as written.** Nothing is amended, nothing is declined, no ratification is left open (D6's frozen-install precondition is a separate, still-open fact — see below), and **build phases MAY start: Phases 1, 2 and 3, in that order.** ⚠ **Phase 4 may NOT start: D6's frozen-install confirmation was NOT given.** ⚠ **Nothing is built.** *(added 2026-10-02 — Phase 1: that was the state at the close; Phase 1 was built afterwards the same day — see `#### Phase 1 record`)*

Every statement in this record is dated 2026-10-02 unless it names another date.

**How it closed — 2026-10-02.**

- **The occasion.** The orchestrator presented every recommendation in this section to the maintainer: D1, D2, D3, D4, D5, D6 and OQ-1.
- **The directive.** A **single blanket maintainer directive**, given in Ukrainian. English translation: *"accept the best decision"*. It names no outcome for any item, so each outcome below is this plan's standing RECOMMEND, taken as written under that directive. **No per-item deliberation was supplied, and no sentence here may be read as the maintainer having weighed any individual counter-argument.**
- **Pick or delegation (`98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md`'s D1 distinction).** **No outcome is an explicit pick** — the directive names no outcome for any item — **and the orchestrator classes every outcome as a DELEGATION to this plan's standing recommendations**, so each outcome is attributed to the orchestrator's recommendation as delegated by the maintainer, and **not to a maintainer choice per item.** ⚠ **That classification is the orchestrator's.**
- **What the directive does NOT supply.** It ratifies D6's recommendation. It does not supply D6's factual precondition, which is the maintainer's statement that the consumer install is NOT the frozen benchmark install. A ratification of a recommendation is not a statement of fact about an install.
- **Every counter-argument stays.** D1's, D2's, D4's, D5's and D6's **Counter-argument, recorded** lines, D3's **Con:** line and OQ-1's **Alternative:** stay where they are written, present and unshortened. This close deletes, shortens and answers away none of them. Phase 0's lead-in sentence *"Nothing below is ratified."* records the pre-close state and is kept as written, with a dated parenthetical beside it naming this close; this record supersedes it.
- ⚠ **Ratification changes no evidence class:** ONE observed consumer incident; the mechanism REPRODUCED in this tree; the fix verified in a SCRATCH COPY only; nothing measured.

**Outcomes — 2026-10-02.**

| Item | Outcome | What it settles |
|---|---|---|
| **D1** | Ratified — **Option A** | `from _shared.bug_file import file_bugs`, kept function-local inside `cmd_file_bugs` (Phase 1). Option B, the module-top hoist, is not taken and stays re-openable. |
| **D2** | Ratified as proposed | In-process `main([...])` test(s) in `tests/lib/_verify/test_bugs.py`, through a `_capture` helper, asserting what D2 lists (Phase 1). **Red-before-green is MANDATORY**, and the red must be the F1 ImportError (Trap 7). |
| **D3** | Ratified — **INCLUDE** | The guard file is **`tests/lib/test_relative_import_depth.py`**; the maintainer did not rename it. **Phase 2 RUNS**, implementing D3's contract and its mandatory mutation check. |
| **D4** | Ratified — **Option A** | F11 becomes a new numbered `FINDINGS.md` entry, written in Phase 3. Option B is not taken, and `src/commands/verify/main.md` is not edited (`## Non-goals`). |
| **D5** | Ratified — **125 builds ahead of the queue, and so ahead of plan 108** | One exception to the numeric-order rule. Dated fact, 2026-10-02: another session committed `79d556c` (*"docs(plan-108): re-check against the live tree — R1–R4 recorded, still nothing built"*). It touches only `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`, so plan 108 is still unbuilt and nothing overlaps this plan's files. |
| **D6** | Ratified as proposed — **frozen-install confirmation NOT given** | The four-step surgical delivery stands, and `install.sh` and `update.sh` stay forbidden against that install. **Phase 4 does not run until the maintainer gives the confirmation**; the blanket directive is not that confirmation. Phases 1–3 do not wait on it. |
| **OQ-1** | Ratified — **`### Fixed`** | Phase 3's `CHANGELOG.md` line goes under `### Fixed` in `## [Unreleased]`, added after `### Changed` when still absent at build time, re-verified LIVE at build time. The `### Changed` Alternative is not taken. |

#### Verify

- The record names **each** of D1, D2, D3, D4, D5, D6 and OQ-1 with an explicit outcome (ratified / amended / declined), **checked BY NAME, never against a range**.
- **D3's outcome states include or decline, and on include names the guard's file** — Phase 2's existence depends on it.
- **D5's outcome states whether 125 builds ahead of 108.**
- **D6's outcome records whether the frozen-install confirmation was given.**
- **OQ-1's outcome names the sub-heading.**
- **Every counter-argument above is still present, unshortened.**

---

## Phases

Phase 0 is the section above; **nothing below starts before its close record exists.** **Build order: Phase 1 → Phase 2 → Phase 3.** Phase 2 follows Phase 1 because its mutation check reverts and restores the fixed line. Phase 4 needs only Phase 1's commit.

Every phase commits by explicit path — **never `git add -A`** — because another session builds in this checkout. Commit subjects take the `<type>(plan-125): Phase N — …` form, matching the `feat(plan-107): Phase 3 — …` style `git log --oneline -5` shows.

### Phase 1 — The fix and its regression test (D1 + D2)

**Route: python-engineer → python-reviewer, looping until the review is clean.** Each test is written AND run in the same turn.

#### Deliverables

- The D2 test(s) in `tests/lib/_verify/test_bugs.py`, written FIRST and run against the unfixed line.
- `src/devforge/lib/_verify/_cli.py` — the import line per D1's ratified option. ⚠ **Re-anchor by searching `from .._shared.bug_file`, never by the digits** (Trap 4).
- `test_bugs.py`'s `Coverage:` docstring block names the new verb test(s).
- **This plan** — `#### Phase 1 record` below.

#### Verify

- **RED before the fix:** the new test ERRORS with `ImportError: attempted relative import beyond top-level package`, recorded with the command that produced it.
- **GREEN after, targeted first:** the new test passes, and `python3 -m pytest tests/lib/_verify tests/lib/_shared -q` is green.
- **Then the full suite:** `python3 -m pytest tests/lib -q` is green.
- The F7 launcher repro, run with a synthetic one-issue payload into a temp dir, exits 0 and writes exactly one `001-*.md` carrying `**Source**: verify`.
- `grep -rn 'from \.\._shared' src/devforge/lib/_verify/` returns nothing.
- `git show --stat` lists no file outside `src/devforge/lib/_verify/_cli.py`, `tests/lib/_verify/test_bugs.py` and this plan.
- python-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 1 record

**BUILT 2026-10-02.** **D1 (Option A) and D2 are in the tree: `cmd_file_bugs` imports `file_bugs` by its absolute name, and `TestFileBugsCliVerb` calls the verb.** Route: python-engineer → python-reviewer, looped until clean. ⚠ **Phase 4 has not run, so this plan has delivered nothing to the consumer install.**

Every statement in this record is dated 2026-10-02 unless it names another date.

⚠ **The build moves one part of the evidence class:** the fix, verified in a SCRATCH COPY only at planning (F8), is now verified in this tree by the RED, GREEN and launcher items below. ONE observed consumer incident, the mechanism REPRODUCED in this tree, and nothing measured all stand unchanged.

**Built.**

- **D1 — Option A.** In `cmd_file_bugs`, `from .._shared.bug_file import file_bugs` became `from _shared.bug_file import file_bugs`. It stays function-local, and no comment was added. `git diff --stat` shows `_cli.py | 2 +-`.
- **D2 — `TestFileBugsCliVerb`**, a new class in `tests/lib/_verify/test_bugs.py`, calls `_verify._cli.main` in-process through a module-level `_capture(argv)` helper, copied from `tests/lib/_verify/test_scope.py:100` with `verify_main` as the callee. D2 named that helper and `tests/lib/_fix/test_close_bug.py:58` as the shape. The idiom is copied per module, not shared: `grep -rn '^def _capture(' tests/` returns 12 module-level definitions, this one included. The module gained `import io`, `import json` and `from _verify._cli import main as verify_main`, the import `test_scope.py:33` makes, aliased here.
  - `test_verb_writes_bug_file_and_prints_paths` builds its one issue from the existing `_issue()` fixture, so the payload is synthetic. It asserts each D2 item: return code 0; exactly one file in `--bugs-dir`; stdout JSON equal to the list of written paths; that file contains `**Source**: verify`.
  - `test_verb_empty_issues_prints_empty_array` asserts return code 0, stdout `[]` and no bugs dir created. It goes beyond D2's list — see the departures below.
- **The `Coverage:` docstring block** gained a `TestFileBugsCliVerb` entry naming both tests.

**Verify, item by item.**

- **RED before the fix.** `python3 -m pytest tests/lib/_verify/test_bugs.py -q -k CliVerb`, run against the unfixed line, gave `2 failed`, both on `ImportError: attempted relative import beyond top-level package` raised at `src/devforge/lib/_verify/_cli.py:1080`. pytest counts an exception raised inside a test body as failed, not as an error; the exception is the F1 ImportError, so this is the red Trap 7 requires. The python-reviewer reproduced the same RED independently on a scratch copy of `src/devforge/lib` with the old line restored, through the launcher and in-process, and confirmed both new tests fail on exactly that ImportError.
- **GREEN after, targeted first.** `tests/lib/_verify/test_bugs.py` alone: 49 passed, 3 subtests passed. `python3 -m pytest tests/lib/_verify tests/lib/_shared -q`: 1470 passed, 37 subtests passed — the 1468 baseline in `### Honest bounds` plus the 2 new tests. ⚠ That targeted run collected `test_bugs.py` before the nit fix — see the honest bound below.
- **Then the full suite.** `python3 -m pytest tests/lib -q -p no:cacheprovider`, the Verify command with the baseline run's `-p no:cacheprovider`: **12005 passed, 16 skipped, 27 warnings, 238 subtests passed in 959.02s (0:15:59)**, exit 0. That is the 12003 baseline plus the 2 new tests, with the baseline's 16 skipped, 27 warnings and 238 subtests unchanged. ⚠ This run collected `test_bugs.py` before the nit fix — see the honest bound below.
- **F7 launcher repro.** `python3 src/devforge/lib/verify_helper.py file-bugs --issues <synthetic one-issue json> --bugs-dir <tmp>/bugs --date 2026-10-02` exited 0, wrote exactly one file, `001-null-cart-total.md`, and printed its path as a JSON array; that file carries `**Source**: verify`. `<tmp>` was removed afterwards. The python-reviewer reproduced the run.
- **Grep.** `grep -rn 'from \.\._shared' src/devforge/lib/_verify/` returns nothing.
- **`git show --stat`.** This record ships inside the Phase 1 commit, so it states that commit's content instead of quoting its output: exactly `src/devforge/lib/_verify/_cli.py`, `tests/lib/_verify/test_bugs.py` and this plan. The commit's SHA is recorded in `#### Phase 3 record`.
- **Review.** Round 1 returned SHIP-READY with one nit, fixed as recorded below. Round 2 returned SHIP-READY.

**Departures from the plan text, and additions beyond it — each by name:**

- **`test_verb_empty_issues_prints_empty_array` is beyond D2's list.** D2 lists assertions for a one-issue call only. The engineer added this test to pin the empty-list contract `cmd_file_bugs`'s docstring states (*"empty issues list = empty output, not an error"*). The test count stays inside D2's "one to three tests".
- **The round-1 nit, fixed in that test.** Its final assertion was `assertFalse(os.path.isdir(d) and os.listdir(d))`, which passed whether the bugs dir was absent or empty. It became `assertFalse(os.path.exists(self.bugs_dir))`, because `file_bugs` returns `[]` on an empty list (`src/devforge/lib/_shared/bug_file.py:306`) before it calls `os.makedirs`. The `Coverage:` line now reads "no bugs dir created".

⚠ **Honest bound — which form each run collected.** The full-suite run started BEFORE the round-1 nit fix, so it collected `test_bugs.py` with the weaker assertion. The targeted `tests/lib/_verify tests/lib/_shared` run (1470 passed), the engineer's run in the first Phase 1 report, also ran before the nit fix and collected that same earlier form. After the fix, only `tests/lib/_verify/test_bugs.py` was re-run, 49 passed each time: once by the engineer, and once by the python-reviewer in round 2. Phase 2's Verify requires a full `tests/lib` run, and Phase 2 is committed after this commit, so the full run in its Verify covers the final form — see `#### Phase 2 record`.

### Phase 2 — The class-wide guard (D3) — runs only on a ratified D3

**Route: python-engineer → python-reviewer, looping until the review is clean.** ⚠ **This phase's existence is a ratified-decision dependency, not a judgment call:** if the close record ratifies D3, the phase runs as written; if the close record declines D3, a **SKIPPED BY RULING** line citing the close record's D3 line is written under `#### Phase 2 record`, and no guard file is created.

#### Deliverables

- The guard file D3's ratified outcome names, implementing the contract D3 states.
- **This plan** — `#### Phase 2 record` below.

#### Verify

- The guard passes on the tree, and the 12 healthy F9 sites pass with no allow-list entry.
- **The 3 `SyntaxWarning`s in pytest's warnings summary are EXPECTED, not a failure** — they are plan 121's (Trap 8).
- **Mutation check:** with `:1080` temporarily reverted to its broken form `from .._shared.bug_file import file_bugs`, the guard fails and its message names `_verify/_cli.py`; the line is then restored and `git diff src/devforge/lib/_verify/_cli.py` is empty.
- **Targeted first:** `python3 -m pytest tests/lib/test_relative_import_depth.py tests/lib/_verify -q` is green (with the guard's ratified file name substituted). **Then the full suite:** `python3 -m pytest tests/lib -q` is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 2 record

**NOT RUN.**

### Phase 3 — Ledgers

**Route: instruction-author → instruction-reviewer, looping until the review is clean.** Docs and ledgers only.

#### Deliverables

- **`CHANGELOG.md`** — one `- fix(verify): …` line under `## [Unreleased]`, under the sub-heading OQ-1 ratified. It says the verb raised on every call and that one consumer install observed it, and it claims nothing measured.
- **`FINDINGS.md`** — the F11 entry per D4's ratified outcome, numbered after the last entry present at build time, in entry 7's shape. Its heading carries no `— original position:` clause. Its closing NOTE ON THIS ENTRY'S SHAPE mirrors entry 7's, which reads *"the SEVENTH file-less finding and the second recorded after the 2026-08-17 relocation, so, like entry 6, its heading carries **no `— original position:` clause**, and one must not be invented for it"*: the new note says the EIGHTH file-less finding and the third recorded after the 2026-08-17 relocation. ⚠ **The ordinal notes inside entries 1–7 stay unedited**, per that file's preamble.
- **`PLAN-STATUS-ARCHIVE.md`** — three edits, in one change:
  - **(1)** this plan's `## Index` line and **(2)** its `## Entries` record, **both shapes or neither**, per that file's `## Index` preamble (`:9`);
  - **(3)** the `## Index` paragraph that summarizes `FINDINGS.md` (`:99`), which opens with the literal *"Seven file-less FINDINGS"*: "Seven" becomes "Eight", and an "(8) …" clause naming the new finding is appended after the existing (7) clause. Otherwise it under-counts the file it summarizes.
- **This plan** — its Status line and `#### Phase 3 record` below.

#### Verify

- `grep -n "fix(verify)" CHANGELOG.md` shows the new line above `## [2.0.12]`, under the OQ-1 heading.
- `grep -n "^## " FINDINGS.md` shows the new entry last; `grep -n "EIGHTH file-less finding" FINDINGS.md` finds its closing note; `git diff FINDINGS.md` shows additions only.
- In `PLAN-STATUS-ARCHIVE.md`, `grep -n` finds each of the three lines: this plan's `## Index` line (above `## Entries`), its `## Entries` record (below `## Entries`), and the FINDINGS paragraph opening *"Eight file-less FINDINGS"* with its "(8)" clause.
- The maintainer greps the staged diff for the consumer's identifiers (held outside this repo) and gets no hit.
- `git show --stat` lists only this phase's files.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 3 record

**NOT RUN.**

### Phase 4 — Consumer delivery (D6) — user-driven, NOT run by default

⚠ **Run by the user, outside this repo, only after Phase 1 has landed and D6's precondition is confirmed.** Nothing in Phases 1–3 waits on it.

#### Verify

- Both D6 step-2 `diff` results are recorded, with the import line as the only delta.
- The consumer's `file-bugs` call exits 0 and writes one `bugs/NNN-*.md` per issue, numbered after that install's highest existing `NNN` (`verify/main.md:441`), each carrying `**Source**: verify`.
- The outcome is recorded below with no client identifier.

#### Phase 4 record

**NOT RUN.**

---

## Non-goals

- **No change to `src/commands/verify/main.md`.** F11's orchestration question goes to `FINDINGS.md` (D4), not into an edit.
- **No change to `src/devforge/lib/_shared/bug_file.py`.** The writer is correct (F8); only its import was wrong.
- **No subprocess test harness.** F7 shows the in-process call reproduces the launcher.
- **No sweep of other lazy imports beyond D3's guard.** The 12 healthy F9 sites are correct (Trap 6).
- **No edit to `27-REPORT-BUG-COMMAND-PLAN.md`.** It prescribed the broken line (F5), and its record is frozen.
- **No release cut.** The CHANGELOG line lands under `## [Unreleased]`.
- **No scan of `scripts/` by D3's guard.** Code there loads under a topology this plan has not examined.

---

## Context for next session

⚠ **Evidence class: ONE observed consumer incident; mechanism reproduced in this tree on 2026-10-02; fix verified in a scratch copy only; nothing measured.** *(added 2026-10-02 — Phase 1: as of Phase 1 the fix is verified in this tree as well — see `#### Phase 1 record`; nothing measured still holds, and the form to repeat is the Phase 1 note at the top of `## Origin & evidence`)* ⚠ All line digits drift — **grep the quoted text, never the digits.**

**The one sentence that governs everything here:** **`/devforge:verify` cannot file bugs in any install carrying `from .._shared.bug_file import file_bugs`; the fix is the absolute import every other site uses; and the suite stayed green because the import is lazy and no test calls the verb.**

### Honest bounds

- **One incident, nothing measured.** How many installs reached an elected PHASE 9 filing since 2026-06-19 is unknown.
- **D2 protects one verb.** Without D3, the next lazy over-deep relative import is as invisible as this one was.
- **D3 catches one shape:** a relative import that climbs above its top-level package under `src/devforge/lib/`. It does not catch an absolute import of a package an install does not ship.
- **F8 is not a tree verification.** Until Phase 1's Verify passes, the tree's line is broken. *(added 2026-10-02 — Phase 1: Phase 1's Verify passed, so the tree's line is fixed — see `#### Phase 1 record`)*
- **The fix restores the verb; it does not make PHASE 9's failure path safe.** F11 stays open in `FINDINGS.md`.
- **Both pre-fix baselines are recorded, and both are green.** `python3 -m pytest tests/lib/_verify tests/lib/_shared -q` was green on 2026-10-02 (1468 passed, 37 subtests passed, Python 3.13.5). The full run started in the planning session on 2026-10-02, `python3 -m pytest tests/lib -q -p no:cacheprovider`, outlasted a 600-second tool timeout and completed later that day in the background, against `src/` and `tests/` as of `8e61645`: **12003 passed, 16 skipped, 27 warnings, 238 subtests passed in 964.18s (0:16:04)**, exit code 0. `79d556c`, which landed the same day, touches only a plan markdown file. Other pytest processes shared the machine during the run, so its duration is no measurement of the suite's speed. **That result is the pre-fix green baseline Phase 1's full-suite Verify compares against.**

### Traps

**Trap 1 — a green suite is not evidence the verb runs.** The import is lazy, and before D2 no test called the verb (F6).

**Trap 2 — client identifiers.** This file is tracked in a public repo. Describe the consumer generically, every time.

**Trap 3 — `git add -A`.** Another session builds in this checkout. Commit by explicit path, and check `git show --stat` after every commit.

**Trap 4 — line digits.** Re-anchor `_cli.py:1080` by searching `from .._shared.bug_file` before editing; after Phase 1 that search returns nothing by design.

**Trap 5 — the consumer's scratch payload is gone.** The chained Cleanup deleted `issues.json` (F11). Recompose it in that consumer session, and never copy it into this repo.

**Trap 6 — "normalizing" the healthy `from ..` sites.** The 12 F9 sites sit at depth 2 or 3, where `..` resolves inside the top-level package. Rewriting them is churn with breakage risk, and it is not this plan.

**Trap 7 — a RED for the wrong reason.** D2's red must be the F1 ImportError. A failing assertion, a fixture error or a typo is not the red this plan requires.

**Trap 8 — plan 121's warnings inside D3's scan.** `121-HELPER-SYNTAX-WARNINGS-PLAN.md:8` records `SyntaxWarning: invalid escape sequence` and names two files; those two files hold three sites. Verified 2026-10-02 on Python 3.13.5: `ast.parse` over all 334 `.py` files under `src/devforge/lib/` (`__pycache__` excluded) emits exactly 3 `SyntaxWarning`s — `_generate_docs/_md_frontmatter.py:21`, `_generate_docs/_md_frontmatter.py:92` and `_configure/_lint_ignore.py:632` — and every parse succeeds. No warnings-as-errors config exists: the repo root has no `pytest.ini`, `pyproject.toml`, `setup.cfg` or `tox.ini`, and `tests/conftest.py` has no warning filters. So the guard passes and pytest prints those 3 warnings in its summary. The guard does not filter them; plan 121 owns them.

### File anchors

**EDIT targets — a phase of this plan writes each of these:**

- **`src/devforge/lib/_verify/_cli.py`** — `:1080`, inside `cmd_file_bugs` (`:1069`) (Phase 1).
- **`tests/lib/_verify/test_bugs.py`** — the D2 test(s) and its `Coverage:` docstring (Phase 1).
- **`tests/lib/test_relative_import_depth.py`** — new, under D3's ratified name (Phase 2).
- **`CHANGELOG.md`**, **`FINDINGS.md`**, **`PLAN-STATUS-ARCHIVE.md`** (`## Index`, `:99`, `## Entries`) (Phase 3).

**READ-ONLY anchors — no phase of this plan writes any of these:**

- `src/devforge/lib/verify_helper.py:16`–`:20` — the launcher's `sys.path` insert and absolute import; `04-PR-REVIEW-PLAN.md:126` — the earlier record of that topology (F2).
- `src/commands/verify/main.md:408`–`:468` — PHASE 9, the `:419` call, `:441`'s end-the-turn rule, and Cleanup (F4, F11).
- `src/devforge/lib/_shared/bug_file.py:284` — `file_bugs`, with its `source="verify"` default.
- `src/devforge/lib/_verify/_cli.py:159`, `src/devforge/lib/_report_bug/_cli.py:82`, `src/devforge/lib/_fix/_cli.py:302`, `src/devforge/lib/_shared/ticket_file.py:106` — the absolute convention (F3).
- `27-REPORT-BUG-COMMAND-PLAN.md:28` — the instruction that produced F1 (F5). **Frozen.**
- `tests/lib/_verify/test_preflight.py:730`–`:757` — registration only (F6).
- `tests/lib/_verify/test_scope.py:100` and `tests/lib/_fix/test_close_bug.py:58` — the `_capture` precedent (D2); `tests/lib/_review/test_report.py:840`–`:868`, `tests/lib/_specify/test_verify_change_kind_coherence.py:284` and `tests/lib/test_agent_reachability.py` — the AST-scan and live-`src/` gate precedents (D3).

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation.
2. **Check `### Phase 0 close record` first.** Phase 0 closed 2026-10-02: D1–D6 and OQ-1 are ratified as recommended, so Phases 1, 2 and 3 may build, in that order. **Phase 4 does NOT start until the maintainer gives D6's frozen-install confirmation** — the blanket directive was not that confirmation, and the record still says so. *(corrected 2026-10-02 — Phase 0 close: this step read "While it reads PENDING, nothing is ratified and no build phase may start.", which held until the close)*
3. **See what landed:** `git log --oneline -- src/devforge/lib/_verify/_cli.py tests/lib/_verify/test_bugs.py`.
4. **Re-run the F7 launcher repro.** Before Phase 1 it raises the F1 ImportError; after Phase 1 it exits 0. ⚠ **After Phase 1, `grep -rn "from \.\._shared.bug_file" src/` returning nothing is the built state, not drift.**
5. **Re-verify F1–F11 by grepping the quoted text, never the digits.** F5's and F10's commit facts are re-derived with `git`, not with a file read.
6. **Route every edit through the house flow:** python-engineer → python-reviewer for every Python edit; instruction-author → instruction-reviewer for every markdown edit; each loop runs until its review is clean. **Commit by explicit path, never `git add -A`.**
7. **Keep the evidence class** (stated at the top of `## Origin & evidence` and of `## Context for next session`) **and the no-client-identifier rule** (`## Origin & evidence`, Trap 2) **attached** to every summary of this plan. *(added 2026-10-02 — Phase 1: from Phase 1 on, the class to attach is the form in the Phase 1 note at the top of `## Origin & evidence` — the fix is verified in this tree as well, and nothing measured still holds — never the original "SCRATCH COPY only" wording)*
