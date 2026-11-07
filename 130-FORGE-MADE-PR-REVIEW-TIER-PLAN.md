# 130 — Forge-Made PR Review Tier Plan

**Created**: 2026-10-04
**Status**: **Phase 0 OPEN — nothing below is ratified, no close record exists, and no build phase may start. Nothing is built and nothing is measured.** ⚠ **Evidence class, repeated in every summary of this plan: the live tree VERIFIED by read and grep on 2026-10-04; PUBLIC Claude Code documentation — `code-review.md` and `ultrareview.md`, plus one section of `skills.md` — fetched on 2026-10-04; NOTHING built and NOTHING measured by this plan.** ⚠ **It EXTENDS the built `/devforge:pr-review` (`04-PR-REVIEW-PLAN.md`) with a second arm; the foreign-PR arm keeps its review behaviour, and only its false storage text at `:308` and `:340` is corrected (F3).** ⚠ Numbered 130: a glob of `13[0-9]-*.md` on 2026-10-04 returns nothing; other sessions work here, so re-check. ⚠ **Every `file:line` was read on 2026-10-04 — grep the quoted text, never the digits.**
**Branch:** `develop-2.0-init`

`/devforge:pr-review` reviews a PR whose authoring team is *"unaware of forge"* (F1). When the PR was produced by another developer's forge install, a second forge instance running the same prompts, constitution and memory is a correlated re-roll of the first, not a second pair of eyes. This plan proposes a `forge-made` arm inside the command that does only the work correlation cannot spoil: it fetches the PR's own pipeline record without touching the reviewer's checkout, tries to refute every claim that record makes against the PR head, runs the mechanical gates on the PR head in a throwaway worktree, and hands the generic bug-hunt to the native Claude Code review — and, where the managed product is enabled and the file is committed, a rendered `REVIEW.md` as its rule carrier.

---

## Evidence constraint

Two evidence classes only.

1. **The live tree**, verified by read and grep on 2026-10-04 — every F-item below names its anchor and a quoted phrase to grep.
2. **PUBLIC Claude Code documentation**, fetched by the drafting session on 2026-10-04: `https://code.claude.com/docs/en/code-review.md` and `https://code.claude.com/docs/en/ultrareview.md`, plus — for D3's frontmatter question only — the section "Pre-approve tools for a skill" of `https://code.claude.com/docs/en/skills.md`. A quote is the page's wording on that date. Both review products are labelled research preview on those pages, so their wording changes: re-fetch before building on a quote, and route every Claude Code authoring surface through the `claude-code-guide` agent (house rules).

No client name, install path, ticket id, or benchmark content may enter this file or any file a phase writes. The frozen benchmark install is never touched. **Nothing is measured by this plan: every quality claim below is an argument, not a number.**

---

## Origin

The evidence class in the `**Status**:` line binds everything below.

### The maintainer's question, 2026-10-04

*(paraphrased in English by the drafting session — not a verbatim quote)* Can a PR produced by one developer's forge install be reviewed with quality by a second developer's forge install, both standalone? The goal is to learn the framework's potential for an AUTOMATED cross-developer PR review, and to build the gaps the answer exposes.

**The maintainer's framing, kept as a design constraint** *(paraphrased)*: human PR review is almost always a "bad code" check, not a "right task" check; the forge's unique slice is the "right task" half.

### The session's finding, which this plan encodes

1. A second forge instance runs the same prompts, agents, constitution and memory as the first (`## The load-bearing argument`). It is a correlated re-roll, not a second pair of eyes.
2. The only uncorrelated work a second instance can do is: **(a)** verify the first instance's recorded CLAIMS (F4, F5); **(b)** run MECHANICAL gates on the PR head (F5, F8); **(c)** hand the generic bug-hunt to the native Claude Code review, which runs different prompts and whose two cloud products state a verification step (F9).
3. (a) is the "right task" half; (c) is the "bad code" half; (b) serves both. The forge builds (a) and (b) and delegates (c).

---

## What exists, verified against the live tree (2026-10-04)

**F1 — The command.** `src/commands/pr-review/main.md` (350 lines). `:21` frames it for *"a teammate's pull request against a foreign-repo codebase"* where *"the PR-authoring team is unaware of forge"*; output stays under `.devforge/pr-reviews/<PR#>/` and *"findings are NEVER posted to the PR automatically"*. `description` (`:3`): *"Personal-overlay PR review of a foreign-repo PR"*. Phases: **-1** `ensure-cbm-index`; **0** `detect-forge-state` — `tier` `full` / `partial` / `none`, about the REVIEWER's overlay (`src/devforge/lib/_pr_review/_detect_tier.py`) — plus `read-memory`; **1** `intake` via *"`gh pr view --json` + `gh pr diff`"*; **2** `detect-smells`, eight heuristics (`empty_pr_body`, `atomic_dump`, `hedge_defensive`, `verbose_commit_msg`, `duplication_ratio`, `literal_archaeology_adapter`, `argument_duplication`, `hallucinated_api`); **3 / 3.5** blast-radius probe specs + the CBM `trace_path` fill; **4** `bundle-context` (`:193`) aggregates *"the universal `src/constitution.md`, the per-target `.devforge/constitute.json`, concern overview/architecture docs"*, ADRs and *"all repo-root `*-PLAN.md` files"* — **no `specs/<feature>/` artifact**; **4.5** `import-handoffs` (`:203`) scans only `research-handoff.json` / `discover-handoff.json` *"inside every feature directory under `<target>/specs`"* — the reviewer's own tree; **5** scope drift against ticket text; **6** `dispatch-review` builds `brief.md` (*"Brief size must be under 100 000 chars"*, `:233`); **6.5** (`:235`–`:252`) dispatches `cavecrew-reviewer` via the Task tool, fallback copy *"Cavecrew returned <N> findings. Proceeding to finalize-output with helper-side smells only."*; **7** `finalize-output` renders `findings.md` (`_output.py:270` `"## Summary"`, `:330` `"## Findings"`); **7.5** replay corpus. Frontmatter `allowed-tools` (`:6`–`:16`): `Bash(gh pr *)`, `Bash(gh issue *)`, `Bash(git rev-parse *)`, `Bash(git blame *)`, `Bash(git log *)`, `Bash(grep *)`, three python forms, `Read(.)` — no `git fetch`, `git show` or `git worktree`. Helper package `src/devforge/lib/_pr_review/` (`_cli`, `_dispatch`, `_bundle`, `_blast`, `_detect_tier`, `_ensure_cbm`, `_handoff_import`, `_intake`, `_output`, `_replay`, `_scope_drift`, `_state`, `_validators`, `_smells/`); tests `tests/lib/_pr_review/` (13 top-level `test_*.py` files plus `_smells/`).
- **Two state gaps.** `_intake.py:57`–`:60` requests `files` and `headRefName` from `gh pr view`, but `PRReviewState` (`_state.py:28`–`:60`) carries neither: `files` survives only as a count (`_intake.py:418`, *"len(pr_view.get("files") or [])"*), and no field holds the head ref.
- **No wrapper read.** A grep for `wrapper` over `src/commands/pr-review/` and `src/devforge/lib/_pr_review/` returns nothing; sibling packages emit `wrapper_mode` from a `_preflight.py` that inlines a `CLAUDE.md` substring check (`_review/_preflight.py:137`, `_verify/_preflight.py:144`: `if "wrapper mode" in lower or "wrapper root" in lower:`); `_implement/_workspace.py` `resolve_workspace` (`:130`) returns a `Workspace` (`:63`) with an `is_wrapper` field (`:78`).
- ⚠ **No launcher.** The spec's helper calls invoke `.devforge/lib/pr_review_helper` (`:87`, `:102`, `:114`, `:149` …), but a glob of `src/devforge/**/pr_review*` returns only `pr_review_helper.py`. `src/devforge/lib/` holds 25 extensionless `*_helper` launchers (e.g. `review_helper`: *"# POSIX launcher for review_helper.py."*) and `pr_review_helper` is not among them; inside `install.sh`'s `--only <cmd>` surgical branch (`:103`–`:233`), `:214` copies `"${cmd_u}_helper"` only when the source file exists — the full-install path was not read here. Plan 125 raised this gap (`125-VERIFY-FILE-BUGS-IMPORT-PLAN.md:253`) and records *"no decision given"* (`:304`). Whether a consumer install's first helper call fails was NOT run here — OQ-9.

**F2 — `cavecrew-reviewer` is not shipped.** `src/agents/` on 2026-10-04: ac-verifier, api-designer, architect, backend-engineer, code-reviewer, db-engineer, design-auditor, devils-advocate, devops-engineer, frontend-engineer, game-engineer, migration-engineer, mobile-engineer, performance-analyst, qa-engineer, qa-reviewer, runtime-debugger, security-reviewer, spec-formalizer, tech-writer. `tests/lib/test_agent_reachability.py` records it as a deliberate non-roster external plugin — `test_subagent_nonroster_not_unknown` (`:648`), docstring `:651`–`:652`: *"is NOT a roster agent and NOT a failure"*. A reviewer without that plugin lands on the path the spec names for a failed dispatch (`:252`): Phase 2 heuristics only, zero LLM judgment.

**F3 — Hygiene defects.** `src/files/devforge.gitignore` has NO `.devforge/pr-reviews/` line: it lists `session-state.md`, five per-command JSON files, two stamps, two logs, `*.lock`, `*.preserve` and `profile/` (`:2`–`:14`), then the CODE dirs `lib/`, `bin/`, `templates/`, `command-refs/` (`:17`–`:20`). Since plan 49 the command's storage text is false in three places: `pr-review/main.md:308` *"By default, the install script adds `.devforge/` to the target repo's `.gitignore`"*; the same line's *"a misconfiguration"* for a committed `.devforge/`; and `:340` *"`.devforge/` is gitignored by default (install-script-enforced)"*. `src/devforge/storage-rules.md:102`–`:119` tracks the VERSIONED files (`memory.md`, `spec-stamps.jsonl`, `configure.yaml`, `constitute.json`, `project-config.json` …) and gitignores only the EPHEMERAL and CODE classes; `:117` is the `profile/` EPHEMERAL-subdir precedent row. `scripts/devforge-state-migrate.sh` untracks ten named files, `*.lock` and four CODE dirs (`:28`–`:60`) — it carries no `profile/` entry. **Impact in this plan's setting:** the reviewer's checkout IS a forge install of the same repo, so `state.json`, `brief.md` (which carries the diff) and `findings.md` sit there as untracked files that a `git add -A` commits.

**F4 — A forge-made PR carries its pipeline record.** `src/commands/finalize/main.md:164` *"### Artifact safety-net commit (UNCONDITIONAL, before the squash)"*; `:169` `commit-artifacts --paths '["<feature_dir>/", ".devforge/memory.md", ".devforge/spec-stamps.jsonl"]'`, folded into the squash that `src/CLAUDE.md` describes as *"squash WIP commits into a clean feature commit"*. So the PR's feature commit carries `specs/<feature>/` — among its files `spec.md`, `plan.md`, `tasks/`, `breakdown-handoff.json`, `review.md`, `review-state.json`, `verification.md`, `verify-state.json`, `summary.md` — plus the two runtime deltas. Storage class FEATURE-SCOPED: *"everything under `specs/<feature>/`"* (`storage-rules.md:125`).

**F5 — `/devforge:verify` persists claims with evidence.** `src/commands/verify/main.md:25`: `<feature_dir>/verification.md` *"(AC table, code-quality block, folded review findings, issues, and the verdict)"*. `src/commands/verify/references/report-format.md:33`–`:37`: `| AC | Status | Evidence |`, rows such as `| AC-1 | PASS | [snapshot/response/file:line evidence] |` and `| AC-3 | PASS (code) | … |`; `:14` names EIGHT statuses — *"`PASS` / `FAIL` / `PARTIAL` / `MANUAL` / `PASS (code)` / `FAIL (code)` / `PARTIAL (code)` / `UNVERIFIED`"*. `verify/main.md:265` runs `regression-gate --feature <feature> --workspace-root .`; `:268` says it *"reads the `regression_gate` config itself"* and runs the suite *"at the feature's merge-base in an isolated git worktree and again at HEAD"*. The `ac-verifier` agent (`src/agents/ac-verifier.md:1`–`:6`, `model_tier: verify`; `:9` *"You prove each AC item true or false"*) is dispatched *"with `subagent_type: ac-verifier`"* (`verify/main.md:209`), its mode set by `ac_verification_mode`; `code-only` is *"judge each AC by reading the changed files … No runtime probing, no test execution"* (`ac-verifier.md:39`). Its `tests` mode is described two ways: `:38` *"you do NOT receive live test outcomes. The assembled test suite is a separate mechanical signal run by the orchestrator"*, `:131` *"`tests` relies on the test-suite outcomes and code-reads the rest"*. Its tools include `Bash` (`:4`).

**F6 — `/devforge:review` is destructive on another developer's branch.** `src/commands/review/main.md:25`: `review.md` is *"FINDINGS ONLY (no verdict)"* and *"re-running `/devforge:review` on the same feature OVERWRITES `review.md`"*; `:29` WIP-commits it. Its finders are scoped by `references/anti-relitigation-preamble.md:21`–`:28`: a finding *"fully contained within ONE task's changes"* is out of scope there. Running it on the author's branch overwrites their record and is not a review of the whole diff.

**F7 — The implement panel leaves no trail.** `src/commands/implement/main.md:192` `## PHASE 6: Autonomous review PANEL loop` — four reviewers, *"≤3 rounds"*; scratch at `${TMPDIR:-/tmp}/forge-implement-review/<agent>.md` (`:201`), outside the repo. `review/references/anti-relitigation-preamble.md:32`–`:33`: `/devforge:implement` *"drives each task's findings to clean and writes nothing to disk for this run to compare with"*. No later instance can know what the panel contested.

**F8 — Reusable engines.** `src/devforge/lib/_shared/_verify.py`: `_parse_verdict_block` (`:187`), `route_refutation` (`:289`), `render_verify_brief` (`:374`), `consume_verdicts` (`:465`), `apply_verdicts` (`:564`) — imported by `_audit/_cli.py`, `_grill/_cli.py` and `_review/_cli.py`. `_shared/spec_acs.py:82` `parse_acs`; `_shared/findings_schema.py:90` `class Finding`. `implement_helper run-forcing-functions-gate` (`implement/main.md:221`) dispatches `constitute_helper verify-<rule>` per enabled rule — *"`verify-magic-enum`, `verify-cross-layer-imports`, `verify-any-leak`, and `verify-design-tokens`"* (`:224`). The `devils-advocate` agent. Model tiers: `CLAUDE_TIER_*` keys (`src/devforge/lib/_configure/_render.py:60`–`:79`) and `configure_helper apply-models`.

**F9 — Native Claude Code review, from the public docs (2026-10-04).** THREE products share the name.
- **(a) Local `/code-review`** (`code-review.md`, "Review a diff locally"; the page's opening note: *"On other plans, you can still review a diff locally with the `/code-review` command"*): *"It reports correctness bugs and reuse, simplification, and efficiency cleanups"*; target *"a file path, a PR number, a branch name, or a ref range"*; flags `--fix`, `--comment` (*"posts the findings on a GitHub pull request as inline comments"*), `--max-findings`; *"The review runs as a background subagent with its own context window"*; *"The review follows your `CLAUDE.md` like any Claude Code session, but it doesn't read `REVIEW.md`"*; effort levels *"trade coverage for confidence"*; *"Claude can start `/code-review` on its own"*, and a `skillOverrides` entry `"code-review": "user-invocable-only"` stops that; comparison table: *"Cost | counts toward normal usage"*, *"Depth | scales with the effort argument"*; *"pass a PR number to review a teammate's pull request before approving it"*; *"`/review` is an alias of `/code-review`"*.
- **(b) Ultrareview, `/code-review ultra`** (`ultrareview.md`): *"a fleet of reviewer agents in a cloud sandbox"*; *"every reported finding is independently reproduced and verified"*; *"A review typically takes 5 to 10 minutes"*; *"typically \$5 to \$25 in usage credits"* after three one-time free runs on Pro and Max; the `claude ultrareview` subcommand *"blocks until the remote review finishes, and prints the findings to stdout"*; `--post` posts *"a single plain comment"* that *"isn't a review or an approval"*; *"requires authentication with a claude.ai account and is not available on Amazon Bedrock, Google Cloud's Agent Platform, or Microsoft Foundry, or to organizations with Zero Data Retention enabled"* (`code-review.md`), and *"When ultrareview is not available, `/code-review ultra` runs a local review in your session instead"*. On launch: *"Claude doesn't start an ultrareview on its own"* — but *"When Claude runs the subcommand for you instead, for example through the Bash tool, Claude Code refuses the whole-repository review"*, and *"Running it yourself is what counts as consent"*.
- **(c) Managed Code Review** (GitHub App; *"in research preview, available for Team and Enterprise"*; *"not available for organizations with Zero Data Retention enabled"*): *"multiple agents analyze the diff and surrounding code in parallel … then a verification step checks candidates against actual code behavior to filter out false positives. The results are deduplicated, ranked by severity"*; *"focuses on correctness: bugs that would break production, not formatting preferences or missing test coverage"*; reads `CLAUDE.md` and *"treats newly introduced violations as nit-level findings"*; `REVIEW.md` holds *"review-only instructions, given to the agents that find and verify findings and consulted by the agents that rank and report them"*, and repo-specific checks there *"land more reliably than the same rules in a long `CLAUDE.md`"*; *"a long `REVIEW.md` dilutes the rules that matter most"*; the check run *"always completes with a neutral conclusion"*, its Details text ending in a machine-readable `bughunter-severity:` comment parsed by `gh api repos/OWNER/REPO/check-runs/CHECK_RUN_ID --jq …`; *"completing in 20 minutes on average"*; *"Each review averages \$15-25"*; a fork PR is reviewed only on an `@claude review` comment.
- **Not stated** by either page: whether any of the three reads the PR description, linked issues, or a spec, or runs the test suite.
- **(d) `allowed-tools`** (`skills.md`, "Pre-approve tools for a skill"): it *"grants permission for the listed tools during the turn that invokes the skill"*, *"The grant clears when you send your next message"*, and *"It does not restrict which tools are available"*; a command file *"supports the same frontmatter except `name` and `paths`"*.

**F10 — Ledger anchors.** `README.md:54` (command map, *"/devforge:pr-review"*) and `:91` (*"Personal-overlay review of a foreign GitHub PR"*). `src/CLAUDE.md` names `/devforge:pr-review` nowhere (grep, 0 hits) — not in its `Standalone` list, not in `### Command Details`. The repo-root `CLAUDE.md` router has rows for `/audit` and `/grill` and none for `/pr-review`. `scripts/emitters/claude.py:57` `_PROMOTED` includes `"pr-review"`. `scripts/lib/memory_lane.py:146`–`:152` declares `pr-review` `READS` with the reason *"Reviews a foreign PR's diff for AI-slop, blast-radius, and scope-drift"*. `DEVELOPMENT-STATUS.md` and `CHANGELOG.md` are shared ledgers, re-read live.

---

## The load-bearing argument

**Independence in this framework lives INSIDE a run, not between installs.** The shared refutation router assigns each finding *"the FIRST present finder in the priority order that is NOT the finding's author"* (`route_refutation`, `_shared/_verify.py:289`, docstring `:293`–`:295`), and grill reuses it with an *"architect-excluded `priority=`"* (repo-root `CLAUDE.md`, `/grill` row); the implement panel's reviewers are each *"independent and sees ONLY its own brief"* (`implement/main.md:200`). Between two installs of one repo nothing differs that matters: `memory.md`, `constitute.json` and `project-config.json` are VERSIONED and tracked (`storage-rules.md:106`–`:109`); the reference files are CODE, regenerated by the same emit (`:119`); the agent and command files come from the same framework source. **A second instance re-rolls the same distribution: its agreement with the first is weak evidence, and its disagreement is noise or a real find that cannot be told apart without grounding.**

**What a second instance CAN do without correlation:**
1. **Re-derive the first instance's claims and try to refute each, grounded in the PR head.** `verification.md` states per-AC verdicts with evidence (F5); a claim either re-demonstrates on the head or it does not, and the refuter attacks a concrete evidence cell, not a vibe.
2. **Run the mechanical gates on the PR head.** Detectors and test commands are deterministic; no model sits in the loop (F8).
3. **Hand the generic bug-hunt to a reviewer with DIFFERENT prompts** — the native review, whose managed and ultra products state a verification step (F9) — and feed it the forge's rules through the file it reads: the already-emitted `CLAUDE.md` for the local one and, where the managed product is enabled and the file is committed, `REVIEW.md` as its rule carrier (D5).

**The forge builds only its unique slice** — the "right task" half (1) plus the gates (2). The "bad code" half is delegated (3).

**Not claimed:** that a second forge instance is useless, or that the arm replaces a human. Claimed: its unique value is grounded claim-checking and gates; a second ungrounded LLM pass is the part the native review does with different prompts.

---

## The strongest case against, recorded in full

1. **Native review availability is uneven.** The managed product needs Team or Enterprise and no Zero Data Retention; ultrareview needs claude.ai auth and usage credits after three one-time free runs, and is unavailable on Bedrock, Agent Platform, Foundry and ZDR (F9). Only the local `/code-review` is available outside Team and Enterprise per the page (*"On other plans, you can still review a diff locally"*); its availability per provider is not stated, and its depth *"scales with the effort argument"* — whether it is multi-agent or verifies its findings is not stated. For many reviewers the delegated "bad code" half is a local review of unstated internals.
2. **The claims audit is still the same model family.** A refuter with the author-instance's blind spots can re-reach a PASS the author reached by misreading an AC. Grounding narrows that; it does not remove it. The ceiling is unmeasured.
3. **Running PR code on the reviewer's machine is an execution risk and a cost.** The configured test command and the regression gate — which runs the primary suite at the feature's merge-base and again at HEAD (`verify/main.md:268`, F5) — execute code nobody has reviewed yet. `ac-verifier` carries `Bash` (`ac-verifier.md:4`), so a brief asking it to re-demonstrate a claim can lead it to run code too; its `tests` mode is described inconsistently (`:38` vs `:131`, F5) and the arm does not dispatch that mode (D6).
4. **`REVIEW.md` rendered from the constitution double-enforces rules the emitted `CLAUDE.md` already carries.** The managed product reads `CLAUDE.md` and flags new violations as nits (F9); restating the same rules in `REVIEW.md` produces nits — noise, not signal — and *"a long `REVIEW.md` dilutes the rules that matter most"*, unless `REVIEW.md` carries calibration and skip rules rather than a restatement.

**This case is not answered away.** Ratification is the maintainer weighing it against what the arm buys.

---

## Coordination with neighbouring plans

| Plan | State, 2026-10-04 | Relation |
|---|---|---|
| 04 `04-PR-REVIEW-PLAN.md` | Status line: DRAFTED 2026-05-20; *"ALL 11 HELPER VERBS IMPLEMENTED + slash command spec live"*; Step 12 (a manual end-to-end verify on a real foreign-repo PR) PENDING | The origin of the command this plan extends. Dated note only (OQ-5). |
| 96 `96-PR-READING-GUIDE-PLAN.md` | DONE (build) 2026-09-06; CLOSED 2026-09-07 | The human-reader side of a forge PR; cross-reference only. |
| 109 | Phase 0 CLOSED (`7b0d8d2`); Phases 1–3 committed (`d88a974`, `24b9bd9`, `23af18c`); another session is mid-build, with uncommitted handoff edits in the tree; re-read live | No planned edit to `pr-review/`: its only `pr-review` mention (`:403`) cites `_pr_review/_cli.py` as a `check-*` naming precedent for its own D6 — verify at build. |
| 110 | DECLINED 2026-10-03 (Status line edited, uncommitted, by another session at drafting) | None. |
| 111, 126, 128, 129 | Phase 0 OPEN | A grep of plans 111–129 for `pr-review`, `pr_review`, `devforge.gitignore`, `devforge-state-migrate`, `REVIEW.md` and `_output.py` hits only 125, 126 and 127 (2026-10-04). 126's hits are `src/files/devforge.gitignore`, which it keeps *"byte-unchanged"* (`126-…:340`); second to land re-reads live. |
| 112–124 | Stubs | None known. |
| 125 | DONE (build) 2026-10-02, Phase 4 not run | Raised the launcher gap, *"no decision given"* (F1, OQ-9). |
| 127 `127-CBM-VS-FILES-TOKEN-MEASUREMENT-PLAN.md` | Phase 0 OPEN | Its `:203` counts eleven command files naming CBM tools, `/devforge:pr-review` among them (Phase 3.5); this plan adds no CBM call. Its `:113` cites `devforge.gitignore:4`–`:11` and `:17`–`:20`, digits Phase 1 shifts; second to land re-reads live. |

**Queue:** numeric order. 109 ratified and mid-build by another session (Phases 1–3 committed); 111, 126–129 Phase 0 OPEN; 112–124 stubs; 110 declined; 125 DONE (build). **130 waits behind 109's remaining build, 111 and 126–129 unless the maintainer directs otherwise; the close record fixes the position.**

---

## Non-goals

- **Posting findings to the PR** (`--comment`, `gh pr comment`) — OQ-3, v2.
- **Persisting the implement panel trail** (F7) — OQ-4, a sibling plan.
- **Replacing `cavecrew-reviewer` in the FOREIGN arm** — the foreign arm keeps Phase 6.5 as written.
- **Invoking ultrareview or the managed product from the command** (D4).
- **Wrapper-mode support in v1** (D10).
- **Any change to `/devforge:review` or `/devforge:verify` behaviour** — the arm reads their artifacts and never re-runs them (F6).
- **Any measurement.**

---

## Phase 0 — ratification

Nothing below is ratified. Each of D1–D10 and OQ-2–OQ-10 gives the proposal, recommendation, strongest counter-argument — **recorded, not answered away** — and alternatives, and awaits the maintainer; OQ-1 is answered by the tree. **Every verb, field, flag, path and line of copy is UNRATIFIED until the close record fixes it.** **No emitted sentence names plan vocabulary** ("D3", "plan 130", "Phase 0").

### D1 — Scope: an arm inside `/devforge:pr-review` *(OPEN — awaits the maintainer)*

**Proposal:** a `forge-made` arm INSIDE `/devforge:pr-review`. Phases -1 to 5 and 7 to 7.5 stay shared — intake, the eight heuristics, blast radius and scope drift apply to any PR. When the PR is forge-made, the arm adds detection and fetch (D2, D3), replaces Phase 6.5's dispatch with the claims audit (D6, D8), adds the head gates (D7), and appends the advisory (D4).
**RECOMMEND as proposed** — consistency over invention; the shared phases are already built and tested.
**Counter-argument:** **the spec is already 350 lines, its brief is capped at 100 000 chars (`:233`), and the command's identity — `:21` and `description` (`:3`) — is "foreign repo, author unaware of forge"; the arm contradicts that premise inside the same file.** Two audiences in one spec is the shape that drifts. And "shared" overstates it: on a forge-made diff, Phases 2–5 read the wrong inputs as built (OQ-10).
**Alternatives:** (a) a reference file `references/forge-made-arm.md` carrying the arm's phases — the command's FIRST reference file (`src/commands/pr-review/` holds only `main.md` on 2026-10-04), emitted to `.devforge/command-refs/pr-review/` by `scripts/emitters/claude.py`; (b) a new command — a `_PROMOTED` entry, a new memory-lane disposition, a new emitted surface; (c) extending `/devforge:review` — declined by F6.

### D2 — Detection and naming *(OPEN — awaits the maintainer)*

**Proposal:** a new verb `pr_review_helper detect-pr-kind --pr N` that reads the PR's changed-file list for `specs/**/spec.md` and emits `pr_kind` (`forge-made` | `foreign`), `verified` (`true` when `specs/**/verification.md` is also present) and `feature_dir` (the PR-relative directory). ⚠ **`PRReviewState` holds no file list (F1)**, so the verb either **(i)** parses `state.diff`'s `diff --git` headers — the `_dispatch.py:157` count precedent — or **(ii)** Phase 1 persists `gh pr view`'s `files` on the state (field name UNRATIFIED).
**RECOMMEND** the two-value kind plus the boolean; (i) vs (ii) is the close record's pick.
**Counter-argument:** **a PR carrying `spec.md` but no `verification.md` is a half-run pipeline; treating it as forge-made with `verified: false` routes it to a claims audit with nothing to audit.** Also: detection is by path presence — a PR touching two feature directories' `spec.md` has no single `feature_dir`, and a PR that only edits an older feature's `spec.md` would read as that feature's forge-made PR.
**Alternatives:** a three-value enum (`forge-made-verified` / `forge-made-unverified` / `foreign`); a stop with one plain sentence when two candidates match.

### D3 — Artifact fetch without checkout *(OPEN — awaits the maintainer)*

**Proposal:** `git fetch origin pull/<N>/head:refs/forge-pr/<N>`, then `git show refs/forge-pr/<N>:<path>` per artifact, inside a verb `fetch-pr-artifacts --pr N` that writes them under `.devforge/pr-reviews/<N>/artifacts/`.
**RECOMMEND as proposed** — it never touches the reviewer's checkout, and (unverified — see ⚠ below) it works for fork PRs and spends no GitHub API quota.
**Counter-argument:** **`pull/<N>/head` is a GitHub refspec; GitLab merge requests use `merge-requests/<N>/head` — v1 is GitHub only, stated.** The `refs/forge-pr/<N>` ref persists in the reviewer's clone unless the run deletes it. The remote name `origin` is assumed; Phase 1 derives the repo from `gh repo view` (`:133`), not from a remote name. On `allowed-tools` (F9 (d)): **the grant covers only *"the turn that invokes the skill"*, and `/devforge:pr-review` ends that turn at Phase 1's ticket-source question (`:138`)**; and git run inside the helper's subprocess — the house shape, *"pure filesystem + subprocess (`gh`, `cbm_sync_helper`)"* (`:346`) — is not a Bash tool call. Whether `Bash(git fetch *)` / `Bash(git show *)` entries are needed at all is a build question for the `claude-code-guide` agent.
**Alternatives:** `gh api repos/{owner}/{repo}/contents/<path>?ref=<headRefName>` — needs the head ref, which intake requests but does not persist (F1); a throwaway clone.
⚠ **The ref and hosting facts in this item — fork-PR refs, API quota, the GitLab namespace — are git-hosting behaviour outside this plan's two evidence classes;** Phase 1's fixture and Phase 6 verify them.

### D4 — Native-review delegation *(OPEN — awaits the maintainer)*

**Proposal:** the arm does NOT invoke `/code-review`. `findings.md` gains a `## Native review` advisory block naming `/code-review <PR#>` (available outside Team and Enterprise — F9 (a)) and, when the PR's repository has the managed product enabled and a committed `REVIEW.md` (D5), that file as the rule carrier (which ref is read is not stated).
**RECOMMEND advisory only:** the local review counts toward the reviewer's normal usage and runs as a background subagent whose findings arrive when it completes, not inside the command's flow; ultrareview bills credits, and the docs make running it the user's consent (F9 (b)).
**Counter-argument:** **the docs say *"Claude can start `/code-review` on its own"*, so the orchestrator COULD run it and fold its findings — making the "bad code" half automatic, which is the maintainer's stated goal.** Two further facts: naming `--comment` in the advisory points the user at posting to the PR, against IMPORTANT RULE 1 (*"Findings stay private"*, `:344`) and this plan's posting non-goal; and **"the model cannot launch ultra" is NOT what the docs say** — the slash form is never model-started, but the `claude ultrareview` subcommand run through the Bash tool is described, with only its whole-repository review refused. The non-goal rests on cost and consent, not impossibility.
**Alternatives:** an opt-in `--native` flag that runs the local `/code-review` and appends its text to `findings.md` — the docs name three foreground cases (a second run while one is in progress, non-interactive `-p` / Agent SDK, `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`), none an interactive orchestrator selects per call, and a user's `skillOverrides` can forbid it; the advisory with or without `--comment` — the close record picks the copy.

### D5 — `REVIEW.md` render *(OPEN — awaits the maintainer)*

**Proposal:** a verb `constitute_helper render-review-md` writing `<install_root>/REVIEW.md` from `.devforge/constitute.json`, run alongside every `render` (which writes `<install_root>/constitution.md`, `src/commands/constitute/main.md:15`, `:567`). Content follows the docs' "What you can tune" patterns: **severity calibration** (what Important means for this project), **skip rules** (generated files; checks the project's hooks or CI already enforce), and an **"Always check" list** from the enabled forcing-functions rules — NOT a restatement of the constitution (counter 4). Class: tracked, mirroring `constitution.md`, which `src/manifest.json:37` lists under `projectOwned` (*"NEVER overwrite"* — and `storage-rules.md:123`: `projectOwned` *"DOCUMENTS, it does not ENFORCE"*).
⚠ **What the file can and cannot do (F9):** the docs describe `REVIEW.md` as *"a file at your repository root"* read by the managed GitHub App; the local `/code-review` *"doesn't read `REVIEW.md`"*. The file steers a review of a PR only when the reviewed ref contains the COMMITTED file, and the docs do not state which ref is read. So `REVIEW.md` is a REPO-LEVEL file: rendered at `/devforge:constitute`, tracked, and shipped with the repo for every later PR — never a per-review artifact the arm writes.
⚠ **Unresolved inside the proposal:** it names forcing-functions rules in BOTH the skip list ("already enforced") and the Always-check list. One rule cannot sit in both; the close record states the split — for example, by whether the pre-commit template `src/git-hooks/pre-commit-forcing-functions.sh` is installed.
**RECOMMEND as proposed** — a repo-level render at `/devforge:constitute`, committed with the repo — with the split fixed at the close.
**Counter-argument:** **a second generated root file the user did not ask for; a project without the managed product gets a file nothing reads** — the local review *"doesn't read `REVIEW.md`"* (F9 (a)). An existing install gets it only on its next `/devforge:constitute` render, a human-typed-only command (`src/CLAUDE.md`). In wrapper mode the install root is not the product repo's root, where the managed product reads the file.
**Alternatives:** opt-in via a `constitute.json` flag; render it only when a Claude Code Review check run is detected on a PR — an alternative, not the recommendation, since a file rendered at review time is not committed in the ref under review; fold the write into `render` itself.

### D6 — Claims audit *(OPEN — awaits the maintainer)*

**Proposal:** a new module `src/devforge/lib/_pr_review/_claims.py` with three verbs:
- `extract-claims --pr N` — parses the fetched `verification.md` AC table (all EIGHT statuses, F5) and `review.md` findings into a claims list. Every PASS-family row (`PASS`, `PASS (code)`) is a claim to re-demonstrate; `FAIL`- and `PARTIAL`-family rows are the author's own admissions, carried unaudited; `MANUAL` and `UNVERIFIED` rows carry no claim.
- `render-claims-brief` — ONE brief for `ac-verifier`, dispatched by `subagent_type` in a REFUTE framing: each PASS must be re-demonstrated on the PR head or it does not stand; mode per the rule below.
- `apply-claim-verdicts` — CONFIRMED / REFUTED / UNVERIFIABLE per claim; renders `## Claims` in `findings.md`.

Reuse `_parse_verdict_block`'s grammar and `parse_acs` for AC ids, but as a SIBLING parser — `apply_verdicts` applies verdicts to findings, and a claim is not a finding.
**Mode rule:** v1 always dispatches `ac-verifier` with `ac_verification_mode: code-only`. The reviewer's configured mode is not read, and runtime-only claims are marked UNVERIFIABLE.
**RECOMMEND as proposed**, with three sub-choices fixed at the close:
- **(a) `review.md`'s extraction rule.** `review.md` is *"FINDINGS ONLY (no verdict)"* (F6): a finding asserts a defect, so the claim a forge-made PR makes about it is that it was resolved downstream — and `verification.md` carries the *"folded review findings"* (F5). Which file is the claim's source is open.
- **(b) The verdict vocabulary.** UNVERIFIABLE sits one word from the existing AC status `UNVERIFIED` (F5), and a reader of `## Claims` beside `verification.md` will conflate them; whether "tried and not re-demonstrated" and "this mode cannot check it" are one verdict or two is open.
- **(c) Grounding.** `code-only` must read the PR HEAD, not the reviewer's checkout: either the brief points the agent at `git show refs/forge-pr/<N>:<path>` (D3's ref; the agent carries `Bash`), or the audit waits for D7's worktree — see `## Phases` ⚠ ordering.

**Counter-argument:** **counter 2 applies in full.** Also: `ac-verifier`'s `runtime-assisted` mode needs the app running from the PR head, which v1 cannot guarantee — the reason for the mode rule — so **a reviewer who configured `runtime-assisted` gets a weaker audit than their own `/devforge:verify` ran.** The arm does not dispatch `tests` mode, whose description is inconsistent (`ac-verifier.md:38` vs `:131`, F5); the suite itself runs only through D7's gates. The agent carries `Bash` (`:4`), so a re-demonstration can still run code (strongest case, item 3). The persona is loaded by `subagent_type`, never re-inlined (`verify/main.md:209`), so the REFUTE framing rides on top of a persona written to *"prove each AC item true or false"*.
**Alternatives:** `devils-advocate` as the refuter; a two-stage confirm-then-refute pass.

### D7 — Mechanical gates on the PR head *(OPEN — awaits the maintainer)*

**Proposal:** a verb `prepare-head-worktree --pr N` creating `git worktree add ${TMPDIR:-/tmp}/forge-pr-review/<N>/worktree refs/forge-pr/<N>` — never the reviewer's checkout — and `run-head-gates --pr N` running the forcing-functions detectors (F8) and, opt-in, the configured test command and the regression gate against that worktree; `git worktree remove` at the run's end (its verb shape is the close record's). Precedent: `regression-gate` already runs *"in an isolated git worktree"* and takes `--workspace-root` (F5).
**Test-execution input:** NOT a command argument — no `arguments` / `argument-hint` change. The arm asks ONE AskUserQuestion at the start of its head-gates step: "Run the PR's test suite in the worktree?" with options `run` / `skip`. A reply that picks neither is not a pick, mirroring the ticket-source question's rule (`:138`, `:144`): the question is asked once more, and a second reply that picks neither is taken as `skip`.
**Detector config (sub-choice):** all four `verify-*` verbs take `--root` and `--config` (OQ-1), so the question is which `constitute.json` governs the detectors on the PR head. **Recommend `--root <worktree> --config <reviewer's .devforge/constitute.json>`**, so the PR author cannot disable the detectors that gate the PR.
**RECOMMEND** static detectors ON by default with the detector config above; test execution only on a `run` pick (counter 3).
**Counter-argument:** **a worktree carries the PR's tracked `.devforge/` files but not `.devforge/lib` (CODE class, gitignored — `storage-rules.md:118`), so the helpers must run from the reviewer's install pointing at the worktree.** And the two configs differ in kind: the worktree's tracked `project-config.json` is the PR head's, the reviewer's install reads its own — which `TEST_COMMANDS[0]` runs, and whether a PR that edits that config can choose its own test command, is open. **Against the detector-config recommendation:** the reviewer's `constitute.json` may lag rules the PR itself introduces.
**Alternatives:** a throwaway clone; no gates in v1, the advisory only; the PR head's `constitute.json` as the detector config, with a diff of the two `forcing_functions` blocks printed; a named test-execution flag instead of the question — rejected because one boolean would cost an `## Arguments` entry, a frontmatter edit and a `claude-code-guide` quote.

### D8 — `cavecrew-reviewer` in the forge-made arm *(OPEN — awaits the maintainer)*

**Proposal:** skip the Phase 6.5 dispatch entirely in the forge-made arm — the bad-code half is delegated (D4) and the plugin is non-roster (F2). The Cost table's *"Every run"* (`:318`) and *"populated exclusively by cavecrew"* (`:244`) become arm-conditional.
**RECOMMEND as proposed.**
**Counter-argument:** **a reviewer with neither the plugin nor native access gets no LLM bug-hunt at all** — the advisory names the local `/code-review`, available outside Team and Enterprise per the page (*"On other plans, you can still review a diff locally"*; provider availability for the local command not stated), but running it is the user's step.
**Alternatives:** dispatch the roster `code-reviewer` with a whole-diff brief; keep the cavecrew dispatch when the plugin is present.

### D9 — `.devforge/pr-reviews/` storage class *(OPEN — awaits the maintainer)*

**Proposal:** EPHEMERAL, gitignored — the line in `src/files/devforge.gitignore`, a row in `storage-rules.md` beside `:117`, a recursive `git rm --cached` entry in `scripts/devforge-state-migrate.sh`, and `pr-review/main.md:308` and `:340` rewritten to name `.devforge/pr-reviews/` instead of `.devforge/` as a whole (F3).
**RECOMMEND as proposed.**
**Counter-argument:** none substantive. Recorded: the replay corpus (Phase 7.5) lives there too and is lost on a fresh clone by design; and the `profile/` precedent shipped a gitignore line and a row but NO migration entry (F3) — whether to add one is the close record's pick.
**Alternatives:** a reviewer-home directory outside the repo; a VERSIONED replay corpus split from the per-PR scratch.

### D10 — Wrapper mode *(OPEN — awaits the maintainer)*

**Proposal:** v1 standalone only; the arm stops with one plain sentence when the install is in wrapper mode, and a foreign PR in a wrapper-mode install still runs the foreign arm unchanged. ⚠ **`/devforge:pr-review` reads no wrapper state today (F1).** `detect-pr-kind` emits a `wrapper_mode` field. No shared wrapper function exists: each sibling `_preflight.py` inlines a `CLAUDE.md` substring check (`_review/_preflight.py:137`, `_verify/_preflight.py:144`); `_implement/_workspace.py` `resolve_workspace` (`:130`) returns a `Workspace` (`:63`) whose `is_wrapper` field (`:78`) is the typed answer; the close record picks which source D10 reads. Built in Phase 1.
**RECOMMEND** v1 standalone with the stop, reading `resolve_workspace` — typed and already tested — over a third inlined substring test.
**Counter-argument:** **wrapper users get nothing.** And `resolve_workspace` lives under `_implement/`, so `_pr_review` would import across packages — that import is a build-time check.
**Alternatives:** resolve `source_root` and fetch from the inner repo — OQ-2.

### OQ-1 — Do the `constitute_helper verify-*` verbs accept an explicit root? *(ANSWERED by the tree, 2026-10-04 — no outcome needed)*

**Verified 2026-10-04: both flags exist on all four verbs — no Phase 4 addition.** `verify-magic-enum`, `verify-cross-layer-imports`, `verify-any-leak` and `verify-design-tokens` each take `--root` and `--config` (`src/devforge/lib/_constitute/_forcing_functions/_cli.py:48`/`:53`, `:70`/`:75`, `:92`/`:97`, `:116`/`:121`); `--config` defaults to *"<root>/.devforge/constitute.json"*. The question that remains — which `constitute.json` governs the detectors on the PR head — is D7's detector-config sub-choice.

### OQ-2 — Wrapper mode beyond v1 *(OPEN — awaits the maintainer)*

**Proposal:** a later plan resolves `source_root`, fetches from the inner repo, and reads the feature record from the install root. **RECOMMEND** defer (D10).
**Counter-argument:** **the wrapper layout keeps `specs/` in the wrapper root (`src/CLAUDE.md`, "Wrapper mode"), so a wrapper-mode PR on the source repo carries no pipeline record at all** — detection by path finds nothing there, and the arm's premise does not hold without a different record source.
**Alternatives:** v1 detects wrapper mode and runs the foreign arm unchanged.

### OQ-3 — Posting to the PR as v2 *(OPEN — awaits the maintainer)*

**Proposal:** v1 never posts (IMPORTANT RULE 1, `:344`). **RECOMMEND** keep for v1.
**Counter-argument:** **an AUTOMATED cross-developer review nobody sees on the PR is half-automated; and between forge users of one repo, the "private overlay" rationale (`:302`, *"the reason `/devforge:pr-review` is private-overlay rather than team-shared"*) no longer holds.**
**Alternatives:** v1 posts one comment behind a flag.

### OQ-4 — The implement panel trail as a sibling plan *(OPEN — awaits the maintainer)*

**Proposal:** a sibling plan persists the panel's contested items so a later instance can audit them (F7). **RECOMMEND** a sibling plan.
**Counter-argument:** **without it the claims audit cannot see what the panel contested — arguably the most valuable claims a forge-made PR carries.**
**Alternatives:** fold it into this plan's Phase 3.

### OQ-5 — CHANGELOG landing and dated notes *(OPEN — awaits the maintainer)*

**Proposal:** lines under `## [Unreleased]` (`CHANGELOG.md:8`; `### Changed` `:10`, `### Fixed` `:18`), plus a new `### Added` block if the close record wants one; a dated note on plan 04's Status line naming this plan. **RECOMMEND as proposed.**
**Counter-argument:** **plan 04's Status line is its own record, with Step 12 still PENDING; a note there edits another plan's history.**
**Alternatives:** no note in plan 04 — this plan's coordination row suffices.

### OQ-6 — Memory-lane gate *(OPEN — awaits the maintainer)*

**Proposal:** `/devforge:pr-review` is a `READS` command (F10), and the gate requires BOTH halves — *"a read is performed AND a consuming surface names the field"* (`storage-rules.md:122`). **The gate is not at risk:** the memory text at `main.md:35`, `:120` and `:239` stays for the foreign arm, so both halves remain in the file. D8 removes the cavecrew dispatch from the forge-made arm only; whether the arm's own step also carries `memory_excerpt` — in the claims brief, under the honesty bound (`:124`) — is a design choice this outcome decides, not a gate requirement. **RECOMMEND** the claims brief carries it; `scripts/lib/memory_lane.py:146`–`:152`'s reason text (*"Reviews a foreign PR's diff"*) is re-worded in the same phase.
**Counter-argument:** **a memory lesson in a REFUTE brief can bias the refuter toward the author-instance's own recorded beliefs — the correlation this plan exists to avoid.**
**Alternatives:** the advisory block as the consuming surface; the arm reads no memory (a disposition change the gate must accept).

### OQ-7 — Agent-reachability gate *(OPEN — awaits the maintainer)*

**Proposal:** dispatching `ac-verifier` by `subagent_type` is already roster-reachable through `/devforge:verify` (`verify/main.md:209`); confirm the gate stays green after Phase 3. **RECOMMEND** confirm only.
**Counter-argument:** **the gate mechanizes type-1 orphaned-agent ONLY (repo-root `CLAUDE.md`), so green says nothing about whether the new dispatch is correct.**
**Alternatives:** a targeted test of the arm's dispatch text.

### OQ-8 — The managed product's `bughunter-severity` one-liner *(OPEN — awaits the maintainer)*

**Proposal:** the advisory also prints the `gh api … --jq` one-liner (F9 (c)) for CI gating when the managed product is in use. **RECOMMEND NO in v1** — the advisory serves a human reviewer; CI gating is outside the command.
**Counter-argument:** **it is the only machine-readable signal any native product emits (F9), and "automated" needs one.**
**Alternatives:** print it only when the PR carries a Claude Code Review check run.

### OQ-9 — The missing `pr_review_helper` launcher *(OPEN — awaits the maintainer)*

**Proposal:** Phase 1 ships `src/devforge/lib/pr_review_helper`, a POSIX launcher in `review_helper`'s shape (F1). **RECOMMEND** yes — every arm, and Phase 6, need the command to run.
**Counter-argument:** **plan 125 asked the maintainer twice and recorded *"no decision given"* (`125-…:304`); bundling the fix here decides by inclusion what the maintainer left open.** And plan 04's Step 12 — the end-to-end verify on a real PR — is PENDING, so nothing records the command running in a consumer install; Phase 6 may surface more than this plan scopes.
**Alternatives:** a `FINDINGS.md` entry (plan 125's "record it" outcome); a standalone fix commit before this plan.

### OQ-10 — The shared phases on a forge-made diff *(OPEN — awaits the maintainer)*

**Proposal:** the forge-made diff carries `specs/**`, `.devforge/memory.md` and `.devforge/spec-stamps.jsonl` (F4), so as built: Phase 2's heuristics and Phase 3's symbol extraction run over markdown and runtime files; Phase 4.5 scans only the reviewer's own `specs/` (F1), not the fetched PR record; and Phase 5 drifts against ticket text, though the fetched `spec.md` is the better "right task" source. **RECOMMEND:** in the forge-made arm, `specs/**` and `.devforge/**` are filtered out of the Phase 2–3 input; Phase 4.5 reads the FETCHED handoffs instead; and Phase 5 uses the fetched `spec.md` as the ticket-text source when the user picks `skip` at the ticket-source question (`:138`).
**Counter-argument:** **three more arm-conditional sentences in a spec that is already long** (D1's counter).
**Alternatives:** leave Phases 2–5 as built and accept the noise; filter only Phases 2–3 and leave 4.5 and 5 unchanged.

### Phase 0 close record

**OPEN — nothing ratified; no build phase may start.** ⚠ **Nothing is built and nothing is measured.** It closes in plan 125's shape (`125-VERIFY-FILE-BUGS-IMPORT-PLAN.md`, `### Phase 0 close record`): occasion; directive (non-English in English translation); pick-or-delegation per `98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md` D1; outcomes table.

#### Verify

- **Each** of D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, OQ-2, OQ-3, OQ-4, OQ-5, OQ-6, OQ-7, OQ-8, OQ-9 and OQ-10 has an explicit outcome (ratified / amended / declined), **checked BY NAME, never against a range.** OQ-1 is answered by the tree and needs none.
- D1 names in-file or reference file; D2 names (i) or (ii) and the two-candidate rule; D3 names the fetch route and the ref's lifetime; D4 states the advisory copy with or without `--comment`; D5 states the forcing-functions split; D6 states (a), (b) and (c) and confirms the `code-only` mode rule; D7 names the test-config source and the detector config source (`--config`); D9 states whether the migration entry ships; D10 states whether the `wrapper_mode` field on `detect-pr-kind` ships and which source it reads (`resolve_workspace` or an inlined substring check).
- **The `## Phases` ordering hazard is resolved** — D6 (c)'s grounding route, or Phase 4 built before Phase 3.
- Every verb, field, flag and path a phase builds is named in the record; nothing UNRATIFIED above ships under its draft name without that.
- The record states 130's queue position, and whether each outcome is an explicit pick or a delegation.
- Every counter-argument and alternative above survives unshortened; `## The strongest case against, recorded in full` is unedited from the close onward — before the close record exists, Phase 0 review may edit it.

---

## Phases

**Nothing below starts before the close record exists. Default build order 1 → 2 → 3 → 4 → 5 (3 and 4 swap if the close record picks the worktree route for the claims audit); Phase 6 is not run by default.**

⚠ **Ordering hazard, recorded:** Phase 3's claims audit must ground in the PR HEAD, but the head worktree arrives in Phase 4. Under D6 (c)'s `git show` route, Phase 3 needs only Phase 1's fetched ref; under the worktree route, Phase 4 builds before Phase 3. The close record picks; this section is rewritten to the pick, so no phase carries an "under route X / under route Y" fork.

### House rules for every phase

- Python: **python-engineer → python-reviewer**; markdown: **instruction-author → instruction-reviewer**; each loops until SHIP-READY.
- Every helper function gets its own test, written AND run the same turn; fixtures round-trip through real producers — `verify_helper render-report` for `verification.md`, `review_helper render-report` for `review.md`, `constitute_helper`'s setters and `render` for `constitute.json` / `constitution.md`, `pr_review_helper intake` with `subprocess.run` patched as `tests/lib/_pr_review/test_intake.py:102` does, and a real git repository fixture for every fetch, show and worktree verb.
- Targeted tests, then `python3 -m pytest tests/lib -q` green; output read via `rtk proxy` plus a file redirect.
- `python3 -m pytest tests/lib/test_memory_lane.py tests/lib/test_agent_reachability.py -q` green — those live-`src/` tests ARE the memory-lane and agent-reachability gates (repo-root `CLAUDE.md`); `scripts/verify-memory-lane.py` and `scripts/verify-agent-reachability.py` are their script entry points.
- Every phase that adds a helper verb updates `pr-review/main.md:29`'s *"orchestrates 12 helper verbs"* and the `## Overview` list in the same commit; the count sweep greps every phrasing of the number.
- Every Claude Code authoring surface (frontmatter `allowed-tools`, `description`) goes through the `claude-code-guide` agent by page and section heading, with a verbatim quote recorded.
- Commit by explicit path (never `git add -A`) as `<type>(plan-130): Phase N — …`; `git show --stat` lists only that phase's files and this plan; the identifier grep over the staged diff finds no client hit.

### Phase 1 — Hygiene, detection, fetch (D2, D3, D9, D10, OQ-9)

#### Deliverables
- `src/files/devforge.gitignore` — the `.devforge/pr-reviews/` line in the EPHEMERAL block (D9).
- `scripts/devforge-state-migrate.sh` — the recursive untrack entry, if D9's outcome ships it.
- `src/devforge/storage-rules.md` — an EPHEMERAL-subdir row beside `:117`.
- `src/commands/pr-review/main.md` — `:308` and `:340` per D9; the detection and fetch step text. The file's half-steps are `.5` only (`3.5`, `4.5`, `6.5`, `7.5`), so a `1.6` would be its first non-`.5` step — the close record may prefer one step carrying both verbs. Frontmatter `allowed-tools` per D3's outcome.
- `src/devforge/lib/_pr_review/` — `detect-pr-kind` and `fetch-pr-artifacts` (UNRATIFIED names), registered in `_cli.py`; the `PRReviewState` field if D2 (ii) is picked; `detect-pr-kind`'s `wrapper_mode` field (D10), from the source the close record picks: each sibling `_preflight.py` inlines a `CLAUDE.md` substring check (`_review/_preflight.py:137`, `_verify/_preflight.py:144`); `_implement/_workspace.py` `resolve_workspace` (`:130`) returns a `Workspace` whose `is_wrapper` field (`:78`) is the typed answer.
- `src/commands/pr-review/main.md` — D10's one-sentence stop when `wrapper_mode` is true.
- `tests/lib/_pr_review/` — spec + verification → `forge-made`, `verified: true`; spec without verification → `verified: false`; no spec → `foreign`; two candidate feature dirs → D2's rule; a wrapper-mode install → `wrapper_mode: true`; fetch against a local bare `origin` carrying the PR ref; the reviewer's `HEAD`, index and working tree unchanged after the fetch.
- OQ-9's outcome: the launcher, if ratified into this phase.

#### Verify

```bash
grep -rn "install script adds" src/              # → nothing
grep -rn "install-script-enforced" src/          # → nothing
grep -rn "a misconfiguration" src/commands/pr-review/  # → nothing
grep -n "pr-reviews" src/files/devforge.gitignore # → one hit
grep -n "pr-reviews" src/devforge/storage-rules.md  # → the new row
```

- **RED first:** the first `detect-pr-kind` test fails because the verb is missing, for no other reason; recorded with its command.
- The `claude-code-guide` quote for `allowed-tools` recorded; the same check reads the frontmatter's `name:` key (`:2`) against F9 (d)'s *"except `name` and `paths`"* and records the answer — no fix here.
- The house rules.

#### Phase 1 record

**NOT STARTED.**

### Phase 2 — `REVIEW.md` render (D5)

#### Deliverables
- `src/devforge/lib/_constitute/` + `constitute_helper.py` — `render-review-md` (UNRATIFIED) per D5's content and split.
- `src/commands/constitute/main.md` — `:15`'s output list names `<install_root>/REVIEW.md`; the render step names the call.
- `src/manifest.json` — `projectOwned` gains `REVIEW.md` beside `constitution.md` (`:37`), per D5's class.
- `src/devforge/storage-rules.md` — **no row:** its disposition table covers `.devforge/` only, and `constitution.md`, the class D5 mirrors, has no row (its only mention is the `.devforge/templates/constitution.md` bullet, `:129`). If the close record wants the file documented, it names where.
- Tests round-tripping through `constitute_helper`'s real setters → `constitute.json` → `render-review-md` → `REVIEW.md`: the severity, skip and always-check sections are present; no section body of the rendered `constitution.md` appears in `REVIEW.md` (counter 4).

#### Verify
- `grep -n "REVIEW.md" src/commands/constitute/main.md src/manifest.json` → hits in both.
- `code-review.md`'s `REVIEW.md` section re-fetched and its quotes in F9 (c) re-checked; any change recorded here.
- The house rules.

#### Phase 2 record

**NOT STARTED.**

### Phase 3 — Claims audit + advisory (D4, D6, D8, OQ-6, OQ-8, OQ-10)

#### Deliverables
- `src/devforge/lib/_pr_review/_claims.py` — `extract-claims`, `render-claims-brief`, `apply-claim-verdicts` (UNRATIFIED), the sibling parser per D6; the brief always sets `ac_verification_mode: code-only` (D6's mode rule).
- `src/devforge/lib/_pr_review/_output.py` — `## Claims` and `## Native review` sections; their placement against `## Summary` (`:270`) and `## Findings` (`:330`) is the close record's; the `## Native review` block per OQ-8's outcome (with or without the `bughunter-severity` one-liner).
- OQ-10's outcome in the arm: `specs/**` and `.devforge/**` filtered out of the Phase 2–3 input; Phase 4.5 reading the FETCHED handoffs; Phase 5 taking the fetched `spec.md` as the ticket-text source on a `skip` pick.
- `src/commands/pr-review/main.md` — the arm's step in place of Phase 6.5's dispatch when `pr_kind` is `forge-made` (a suffixed label such as "6.5-forge" would be the file's first; the close record names it); the memory consuming surface if OQ-6 keeps it; and every sentence the arm makes conditional: `:3` (`description`, `claude-code-guide`), `:21`, `:29`, `:33`, `:35`, `:37`–`:44` (the artefact list), `:120` (memory carried into the cavecrew dispatch), `:124` (*"Every finding still comes from Phase 2's heuristics or Phase 6.5's cavecrew pass"*), `:239`, `:244`, `:252`, `:287` (Verify, *"after Phase 6.5"*), `:297`, `:306`, `:318`, `:324` (total cost), `:330`–`:338` (the Storage tree, which lacks `artifacts/`), `:345`, `:346` (helper surface), `:347` (blast probes travel to cavecrew), `:349` (the cavecrew schema rule).
- `scripts/lib/memory_lane.py:146`–`:152` — the reason text, python loop.
- Tests: fixtures from `verify_helper render-report` and `review_helper render-report`; all eight AC statuses parsed; each verdict applied; the dispatched mode is `code-only` whatever the reviewer configured; `## Native review` rendered on a forge-made PR and absent on a foreign one; on a forge-made diff, no Phase 2 smell and no Phase 3 probe names a `specs/**` or `.devforge/**` path; Phase 4.5 reads the fetched handoffs, not the reviewer's `specs/`; a `skip` pick feeds the fetched `spec.md` to Phase 5.

#### Verify
- `grep -n "cavecrew" src/commands/pr-review/main.md` — every hit is classified as foreign-only or arm-conditional, including `:23`, `:120`, `:178`, `:191`, `:223`, `:347`, `:349`; the classification is recorded.
- If OQ-6 keeps the arm's surface, `grep -n "memory_excerpt" src/commands/pr-review/main.md` hits inside the arm's step; either way the foreign arm's `:35`, `:120` and `:239` still hit.
- The house rules, with the memory-lane and reachability tests named.

#### Phase 3 record

**NOT STARTED.**

### Phase 4 — Head gates (D7)

#### Deliverables
- `src/devforge/lib/_pr_review/` — `prepare-head-worktree`, `run-head-gates` and the cleanup (UNRATIFIED); the detectors invoked with `--root <worktree>` and the `--config` D7's outcome names (the flags exist — OQ-1).
- `src/commands/pr-review/main.md` — the gates step, opening with D7's one test-execution question (`run` / `skip`); a `run` pick is the only route to test execution.
- Tests with a fixture repository: the worktree is created outside the checkout; the reviewer's `HEAD`, index and working tree are unchanged; the worktree is removed at the end; no test command runs without a `run` pick; the detectors read the `--config` D7 names, not the worktree's own `constitute.json` (under the recommended outcome).

#### Verify
- `git worktree list` in the fixture shows no leftover worktree after a run.
- The `arguments:` and `argument-hint:` keys and the `## Arguments` section of `src/commands/pr-review/main.md` are unchanged by Phase 4 (diff against the Phase 3 commit).
- The house rules.

#### Phase 4 record

**NOT STARTED.**

### Phase 5 — Docs and ledgers (OQ-5)

⚠ **Ledger edits wait until other sessions' uncommitted edits to the same files are committed** — `DEVELOPMENT-STATUS.md` carried uncommitted edits at drafting.

#### Deliverables
- `README.md:91` (and `:54` if the map changes).
- `src/CLAUDE.md` — an entry in the `Standalone` list and in `### Command Details` (F10).
- Repo-root `CLAUDE.md` router — a `/pr-review` row naming `_pr_review/`, the forge-made arm and the `REVIEW.md` render.
- `CHANGELOG.md` and `DEVELOPMENT-STATUS.md` per OQ-5; plan 04's dated note per OQ-5.
- `src/devforge/storage-rules.md` — nothing beyond Phase 1's row: the file has no command table (its `## ` headings on 2026-10-04 run from `## Directory Structure` to `## Cleanup Rules`, none a command index).
- `FINDINGS.md` untouched — this plan owns F3; OQ-9 decides the launcher.

#### Verify
- `grep -n "pr-review" src/CLAUDE.md` → hits.
- `git diff CHANGELOG.md` shows hunks only under `## [Unreleased]` (above `CHANGELOG.md:22`, the `## [2.0.12]` heading on 2026-10-04), so every released block is byte-identical.
- The house rules.

#### Phase 5 record

**NOT STARTED.**

### Phase 6 — Consumer e2e — user-driven HARD GATE, DEFERRED by default, NOT run

⚠ **Deferred by default and NOT WAIVED.** Phases 1–5 are build-verified at best, never consumer-validated until this runs; **"done" never means Phase 6 passed.** ⚠ **The frozen benchmark install is never touched; delivery uses the maintainer's surgical-copy practice — helper files copied and the command spec emitted to scratch, never `install.sh` on a frozen install.**

1. **A forge-made PR**, produced by the pipeline from one clone of a consumer install and reviewed from a second clone → `pr_kind: forge-made`; `## Claims` lists every PASS-family row of the PR's `verification.md`; `## Native review` present; the reviewing clone's `HEAD`, index and working tree unchanged; `git status` there does not show `.devforge/pr-reviews/`.
2. **A foreign PR** (no `specs/` in its diff) → today's path, cavecrew dispatch or fallback as written.
3. **A wrapper-mode install reviewing a PR whose diff carries `specs/**/spec.md`** → the forge-made arm's one-sentence stop (D10); nothing written to `.devforge/pr-reviews/<N>/artifacts/`.

#### Verify
- All three anchors scored explicitly. A failure is recorded with its artifacts and mechanism: a wrong `pr_kind` is D2's detection; a missing claim is D6 (a) or the parser; a changed checkout is D3 or D7; no stop in wrapper mode is D10's field.

#### Phase 6 record

**NOT RUN.**

---

## Context for next session

⚠ **Evidence class, repeated in every summary of this plan: the live tree VERIFIED by read and grep on 2026-10-04; PUBLIC Claude Code documentation — `code-review.md` and `ultrareview.md`, plus one section of `skills.md` — fetched on 2026-10-04; NOTHING built and NOTHING measured by this plan.**

**The one sentence that governs everything here:** **a second forge instance is a correlated re-roll of the first, so the forge-made arm does only what correlation cannot spoil — it audits the first instance's recorded claims against the PR head, runs the mechanical gates on that head in a throwaway worktree, and hands the bug-hunt to the native review — and, where the managed product is enabled and the file is committed, `REVIEW.md` as its rule carrier.**

### Honest bounds
- Nothing is measured; every quality claim is an argument.
- The local `/code-review`'s internals — multi-agent, verification — are not stated by the docs (strongest case, item 1).
- The claims audit shares the model family (item 2).
- v1 is GitHub and standalone only (D3, D10).
- Detection is by path presence (D2).
- Whether `/devforge:pr-review` runs at all in a consumer install is unverified (F1, OQ-9).

### Traps
**Trap 1 — reading this as "the second forge reviews the PR instead of a human."** The arm's output is input to a human reviewer (`:21`, IMPORTANT RULE 1); it replaces nobody.
**Trap 2 — running `/devforge:review` on the author's branch** — it overwrites their `review.md` and reviews only emergent cross-task issues (F6).
**Trap 3 — restating the constitution in `REVIEW.md`** — strongest case, item 4; D5.
**Trap 4 — letting the arm invoke ultrareview** — D4. And the reverse misreading: the docs do NOT make it impossible for the model; the subcommand through Bash is described (F9 (b)).
**Trap 5 — running head tests by default** — the suite runs only on a `run` pick at D7's one question, never through a command argument; and `ac-verifier` is always dispatched `code-only`, never in `tests` mode (D6's mode rule).
**Trap 6 — using the reviewer's checkout instead of a worktree** — D3, D7.
**Trap 7 — treating the memory excerpt as a finding** — the honesty bound (`:124`); OQ-6.
**Trap 8 — assuming `cavecrew-reviewer` ships** — F2.
**Trap 9 — conflating the native `/review` alias with `/devforge:review`** — `/review` is an alias of `/code-review` (F9 (a)); `/devforge:review` is the forge's feature-level review (F6).
**Trap 10 — conflating a claim verdict with the AC status `UNVERIFIED`** — D6 (b).
**Trap 11 — trusting that `.devforge/lib/pr_review_helper` exists** — F1, OQ-9.
**Trap 12 — `git add -A` in this checkout** — another session shares it (plan 109 is mid-build with uncommitted edits in the tree), so every commit goes by explicit path only (house rules).

### File anchors

Each phase lists its EDIT targets. **READ-ONLY (F-item sources):** `src/commands/pr-review/main.md` (`:3`, `:6`–`:16`, `:21`, `:29`, `:35`, `:87`, `:102`, `:114`, `:120`, `:124`, `:133`, `:138`, `:144`, `:149`, `:193`, `:203`, `:233`, `:235`–`:252`, `:302`, `:308`, `:340`, `:344`, `:346`); `src/devforge/lib/_pr_review/_intake.py` (`:57`–`:60`, `:418`); `_pr_review/_state.py:28`–`:60`; `_pr_review/_dispatch.py:157`; `_pr_review/_output.py` (`:270`, `:330`); `_pr_review/_detect_tier.py`; `_review/_preflight.py:137`; `_verify/_preflight.py:144`; `_implement/_workspace.py` (`:63`, `:78`, `:130`); `src/devforge/lib/review_helper`; `install.sh` (`:103`–`:233`, `:214`); `tests/lib/test_agent_reachability.py` (`:648`, `:651`–`:652`); `tests/lib/_pr_review/test_intake.py:102`; `src/files/devforge.gitignore`; `scripts/devforge-state-migrate.sh:28`–`:60`; `src/devforge/storage-rules.md` (`:102`–`:119`, `:122`, `:123`, `:125`, `:129`); `src/commands/finalize/main.md` (`:164`, `:169`); `src/commands/verify/main.md` (`:25`, `:209`, `:265`, `:268`); `src/commands/verify/references/report-format.md` (`:14`, `:33`–`:37`); `src/agents/ac-verifier.md` (`:1`–`:6`, `:4`, `:9`, `:38`, `:39`, `:131`); `src/devforge/lib/_constitute/_forcing_functions/_cli.py` (`:48`/`:53`, `:70`/`:75`, `:92`/`:97`, `:116`/`:121`); `src/devforge/lib/_grill/_partition.py` (`:3`, `:27`, `:53` — docstring and comments only, not an importer); `src/commands/review/main.md` (`:25`, `:29`); `src/commands/review/references/anti-relitigation-preamble.md` (`:21`–`:28`, `:32`–`:33`); `src/commands/implement/main.md` (`:192`, `:200`, `:201`, `:221`, `:224`); `src/devforge/lib/_shared/_verify.py` (`:187`, `:289`, `:293`–`:295`, `:374`, `:465`, `:564`); `_shared/spec_acs.py:82`; `_shared/findings_schema.py:90`; `src/devforge/lib/_configure/_render.py:60`–`:79`; `src/commands/constitute/main.md` (`:15`, `:567`); `src/manifest.json:37`; `src/git-hooks/pre-commit-forcing-functions.sh`; `scripts/emitters/claude.py:57`; `scripts/lib/memory_lane.py:146`–`:152`; `README.md` (`:54`, `:91`); `CHANGELOG.md` (`:8`, `:10`, `:18`, `:22`); plans 04, 96, 109 (`:403`), 125 (`:253`, `:304`), 126 (`:340`), 127 (`:113`, `:203`); the three documentation pages (F9).

---

## When resuming work

1. **Read this plan in full**, then `src/commands/pr-review/main.md` in full.
2. **Check `### Phase 0 close record` first.** While OPEN, nothing is ratified and no build phase starts.
3. **Check the queue position** the close record names; plans run in numeric order.
4. **Re-verify F1–F10 by the quoted text.** `grep -n "install script adds" src/commands/pr-review/main.md` still hitting means Phase 1 is unbuilt; a glob of `src/devforge/**/pr_review*` still returning only `pr_review_helper.py` means OQ-9 is unbuilt. Re-fetch the documentation pages before relying on any F9 quote.
5. **Use the house loops**, commit by explicit path, resolve the `## Phases` ordering hazard before Phase 3, and keep the evidence class attached to every summary.
