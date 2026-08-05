# 68 — Intake Owns the Feature Dir

**Status**: Phase 0 DONE — **D1–D9 RATIFIED by the maintainer 2026-08-05** (interactive session). Phases 1–8 NOT STARTED.
**Type**: BUILD plan — artifact-relocation + allocation-ownership move across the two intake lanes (`/research`, `/discover`), their consumer (`/specify`), and every downstream reader.
**Branch**: `develop-2.0-init`.
**Created**: 2026-08-05, from a maintainer-ratified inversion of where intake artifacts live.

---

## Why

`/research` and `/discover` are the **two required intake lanes** for `/specify` — `/specify` Phase 0.4 calls `specify_helper find-handoffs --require` and exits 2 BLOCKED when neither lane produced a handoff. There is no cold-start escape. **Running intake therefore means a spec is coming.**

But today the two lanes write their durable artifacts to top-level, dated, consumer-project directories:

| Lane | Report | Handoff | Conditional extra |
|---|---|---|---|
| `/research` | `research/<date>-<slug>.md` | `research/<date>-<slug>/handoff.json` | `research/<date>-<slug>/probe-script.<ext>` (tier-1.5) |
| `/discover` | `discover/<date>-<slug>.md` | `discover/<date>-<slug>.handoff.json` | — |

…and only later, at `/specify`, does the pipeline allocate the feature directory `specs/NNN-slug/` and create the `spec/NNN-<short-desc>` branch. The feature's own investigation record then lives *outside* the feature it produced, in a differently-keyed namespace (date+slug vs NNN+slug), reachable only through an absolute path stored in a provenance field.

**The ratified inversion: intake owns the feature dir.** The feature directory and the branch are born at the END of a research/discover run, and every intake artifact is written inside `specs/NNN-slug/` from the start. Top-level `research/` and `discover/` are retired for new work.

## Why it matters

The relocation is not cosmetic — it structurally dissolves four defects that are otherwise separate bugs to fix (all four are recorded as D9):

1. **The double-import hole.** `import-handoff` never checks `downstream_links.spec_path` before importing (`_specify/_cmds_handoff.py:209-227`, `:524-526`, `:697-699` — computed and written, never read as a guard), so the SAME handoff can silently seed spec `001` and then spec `002`. Under the new layout the handoff lives *in* exactly one feature dir, so 1-handoff-1-spec is structural rather than policed.
2. **Cross-namespace write-back.** `import-handoff` mutates a file in a foreign top-level directory to back-fill `spec_path`. Under the new layout that becomes a sibling-file write inside the dir `/specify` is already working in.
3. **Two incompatible on-disk layouts.** Research is dir-per-run with a flat sibling md; discover is all-flat. Every consumer glob encodes the asymmetry (`find-handoffs` uses `os.walk` for one lane and `iterdir` for the other). D7 unifies them.
4. **Absolute-path provenance.** `Provenance.upstream_handoff_path` on the specify→plan handoff is an absolute path that `plan_helper render-plan-seeds` follows and dies (exit 2) on when dangling (`src/devforge/lib/plan_helper.py:1390-1470`). Producer and consumer sharing one directory makes a stable feature-dir-relative path possible.

Plus the ordering wart D1 fixes on the way past: `/discover` runs `finalize-handoff` (Phase 4.0, `src/commands/discover/main.md:572-580`) **before** the save prompt (`### Ask to save`, `:582-586`), so a user who answers `skip` is left with an orphaned handoff and no report.

## The change in one picture

**After (both lanes identical — D2 + D7):**

```
specs/NNN-slug/
  research-report.md          # /research report        (lane A)
  research-handoff.json       # /research → /specify    (lane A)
  probe-script.<ext>          # /research tier-1.5      (lane A, conditional)
  discovery-report.md         # /discover report        (lane B)
  discover-handoff.json       # /discover → /specify    (lane B)
  spec.md                     # /specify (unchanged)
  handoff.json                # specify → plan (unchanged, name already TAKEN)
  design-anchor.json          # /specify (unchanged)
  plan.md, research.md, …     # /plan (unchanged; `research.md` name already TAKEN)
```

The two new handoff names avoid the two TAKEN names in that directory: `handoff.json` is the specify→plan handoff and `research.md` is `/plan`'s optional research output. No `intake/` subdirectory.

**Naming note (pre-empting a future "normalization"):** the report stem is `discovery-` while the handoff stem is `discover-`. That asymmetry is the ratified D2 literal. Do not "fix" one to match the other — both names are globbed by `find-handoffs` and by `/pr-review`'s scan; renaming either silently breaks discovery.

**Scratch-vs-record trap (extends plan 49 D7):** `specs/NNN-slug/research-report.md` (a durable RECORD) is a different file from `.devforge/research-report.json` (EPHEMERAL run scratch, gitignored). Same words, different class. `storage-rules.md` must state both.

## Verified code sweep (2026-08-05)

The inventory below comes from a code sweep run during the ratification session. Treat the `file:line` refs as verified **as of 2026-08-05**; re-verify each ref at the start of the phase that touches it (line numbers drift). Where a site is described without a line number, **locate it at build time** rather than guessing.

### Producer side — `/research`

- `src/commands/research/main.md`: report save `:971-975` (declared at `:17`); finalize-handoff `:977-992` (declared at `:18`); probe-script write `:789-806`; commit path-set `:994-1004`; scratch note `:1006-1008`; grill-seed re-entry block `:122-134`.
- `src/devforge/lib/_research/`: `_cmds_handoff.py:138-147` (finalize-handoff; `--emit-handoff-json` is REQUIRED with no default — `_cli.py:259-261`); `_handoff_build.py:410-414` (`research_path` default `research/{date}-{slug}.md`); `_probe_tier.py:169` (tier-1 test path), `:173` (tier-1.5 probe-script default); `_cmds_phase2.py:143` (Next-Step literal "Research reference: research/{date}-{slug}.md"); `_constants.py:13-14` (`.devforge/` run scratch — UNCHANGED); `append-outcome` `_cmds_handoff.py:204-340` + `_cli.py:814-852`.

### Producer side — `/discover`

- `src/commands/discover/main.md`: save prompt `### Ask to save` `:582-586`; report save `:588-592` (declared at `:18`); finalize-handoff Phase 4.0 `:572-580` (declared at `:19`) — **MOVES after the save prompt** per D1; commit path-set `:594-600`; scratch-state note (under `### On skip`) `:606-607`; grill-seed block `:140-152`.
- `src/devforge/lib/_discover/`: `_cmds_handoff.py:86-101` (finalize-handoff — unlike research it HAS a default path `discover/{date}-{slug}.handoff.json`, `_cli.py:584-592` makes the override optional); `_handoff_build.py:500-504`, `:598` (`report_path` default); `handoff_schema.py:989`, `:1014` (`report_path` required non-empty); `_cmds_design.py:316` (Next-Step literal); `append-outcome` `_cmds_handoff.py:180-367` (its md-append already probes two candidate paths at `:340-360`).

### NNN allocation + branch creation (the pieces that move upstream)

- `_next_spec_number(devforge_dir)` — `src/devforge/lib/_specify/_cmds_handoff.py:209-227`. **[VERIFIED this session]** It resolves the repo root as `devforge_dir.parent`, scans `specs/` for `NNN-*` subdirectories, and returns `max+1` (or 1 when none exist). Pure filesystem scan, no state file.
- Branch creation — **[VERIFIED this session]** it is already a helper verb, not raw orchestrator git: `specify_helper create-branch --current-branch <x> --default-branch <y>` (`_specify/_cmds_phase4_setters.py:146-181`, registered `_specify/_cli.py:392`). It requires a spec number + feature slug in state, emits a single `git checkout -b spec/NNN-<slug>` line on stdout when on the default branch, and emits a `# already on non-default branch …` informational comment (no checkout) otherwise. `specify/main.md:507-521` is the orchestrator block that runs it, deliberately in Phase 4 "so the branch number matches the spec directory number" (`:18`, `:73`).
- **[VERIFIED this session — corrects the brief's "default-branch-only guard" shorthand]** `/specify` Phase 0.2 (`specify/main.md:57-74`) is a three-way branch decision, not a boolean: already on a `spec/*` branch → keep it, Phase 4 creation skipped; on the default branch → defer creation to Phase 4; and the helper additionally tolerates a non-default non-spec branch (the `from-here` / `stay` user choice at `:521`). The intake-side port must carry all three arms, not just the default-branch arm.
- Wrapper mode: the branch and all artifacts target the **install root**, matching `commit-artifacts` (`src/devforge/lib/_artifact/_cli.py:44-49`). The source/product repo is never branched or written by intake.

### Consumer side — `/specify`

- `find-handoffs` `_specify/_cmds_handoff.py:730-880` (research `os.walk` + discover `iterdir`); `--require` exit-2 BLOCKED message text; CLI help `_specify/_cli.py:717`, `:723-728`; doc mirror `src/commands/specify/main.md:99-115`.
- `import-handoff` `_specify/_cmds_handoff.py:374-430` (dispatch), research branch `:433-547`, discover branch `:591-722`; `spec_path` back-fill `:524-533` / `:697-707`; `future_spec_path` computation `:472` / `:645`; research slug derivation `_RESEARCH_PATH_SLUG_RE` `:81-85`, `:190-208`, `:473` (discover instead uses `intent.topic_slug` at `:646`); state `source.handoff_path` stored absolute `:510` / `:683`.
- Phase 1 corpus reads: `src/commands/specify/main.md:193-201` (`ls research/` / `ls discover/`); spec-type pre-seeding `:394`, `:416-418` (path-prefix tests); greenfield table `_specify/_schema.py:257-266` + doc `:444`.
- Prefix constants: `_specify/_topic.py:59-72` (`source_origin_for_path` hard-codes `research/`→research, `discover/`→discover, `specs/`→prior_spec); `_specify/_cmds_phase01.py:269-278` (`_group_for_path`); `_specify/_schema.py:270-278` (render-section order).

### Downstream consumers

- `plan_helper render-plan-seeds` `src/devforge/lib/plan_helper.py:1390-1470` + `read-specify-handoff` `:1050-1101` + `src/commands/plan/main.md:60-80` (provenance follow).
- `/plan` skip-with-reference prose `src/commands/plan/main.md:199` ("an existing file under `research/`").
- `/pr-review` `_pr_review/_handoff_import.py:88-119`, `:315-330` (`_scan_research_dir` walks `<target>/research/*/handoff.json`), `_pr_review/_cli.py:317-320`, `src/commands/pr-review/main.md:192`.
- Grill re-entry: the seed-consumer blocks in `research/main.md:122-134` and `discover/main.md:140-152`.
- `src/agents/devils-advocate.md:33` — recon-dossier wording ("the research/discover handoff already on disk"); verify accuracy, likely unaffected.

### Prefix lists that mention `research` / `discover` (decide per site — see Phase 6)

- `_configure/_lint_ignore.py:56-64` `FRAMEWORK_FOLDERS` + doc `src/commands/configure/main.md:402`, `:424`.
- `_verify/_hygiene.py:157-160` skip-segments.
- `_implement/_cmds_verify.py:165-175` `ISOLATION_ARTIFACTS` (includes `research`, not `discover`).
- Docs: `src/devforge/storage-rules.md:7-45` (directory structure), `:88` (FEATURE-SCOPED class), `:94` (scratch≠record), `:180-181` (File Lifecycle); `src/CLAUDE.md` Workflow one-liners + Command Details + the `## Artifact Storage` block; `CHANGELOG.md`; the repo-root `CLAUDE.md` active-plans list.
- `src/files/devforge.gitignore` — **UNCHANGED** (verified: only `.devforge/` entries; no top-level research/discover lines).
- `install.sh` / `update.sh` — **UNCHANGED** (verified: neither creates `research/` or `discover/`).

## Decisions — RATIFIED 2026-08-05 (do not reopen)

### D1 — Allocation happens at intake FINALIZE, not at intake start

The feature dir and branch are created at the END of a research/discover run — at the handoff-write step, after the user confirms saving AND confirms the feature slug. Fixed ordering:

```
confirm save → confirm slug → allocate specs/NNN-slug/ → create branch → write artifacts → commit-artifacts
```

**"Confirm slug" is folded into the EXISTING save prompt — there is no second question.** The one `AskUserQuestion` that already asks whether to save also displays the proposed feature name (2–4 words, kebab-case, derived from the run's `topic_slug`); the tool's built-in "Other" free-text option IS the override path. Precedent + justification: `/specify`'s `assign-feature-name` is a silent validate-only step with no user turn, but at intake the name is locked BEFORE any spec exists and becomes the permanent directory name AND branch name — a one-time visible confirmation is warranted, and it costs zero extra interactions because the save prompt already exists.

A **dead-end run allocates nothing**: "not a bug" (research), build-vs-buy = BUY (discover), or the user declining to save all terminate with zero filesystem footprint outside `.devforge/` scratch.

Rationale: mid-run there are no durable artifacts — all in-run state is `.devforge/` scratch (EPHEMERAL, gitignored, crash-recoverable), and nothing is git-committed mid-run today either. The single exception is the conditional tier-1.5 probe-script, which D8 reroutes through scratch. This ordering also repairs the `/discover` finalize-before-save wart: `finalize-handoff` moves **after** the save confirmation.

### D2 — Flat file names inside the feature dir

`research-report.md` + `research-handoff.json` (+ conditional `probe-script.<ext>`) for lane A; `discovery-report.md` + `discover-handoff.json` for lane B. Chosen to avoid the names already taken in that directory (`handoff.json`, `research.md`). No `intake/` subdirectory.

### D3 — Clean cut: no legacy readers, no dual-glob transition code

New code reads ONLY the new locations. Existing consumer-install `research/` and `discover/` directories stay on disk as inert history; nothing migrates and nothing deletes them.

**Honest scope**: old features' absolute provenance paths keep resolving *only because those files are never deleted* — this is persistence, not compatibility. If a consumer deletes their old `research/` dir, an old feature's `plan_helper render-plan-seeds` provenance follow will hit the existing dangling-path exit-2 path. That is accepted.

### D4 — `append-outcome` / `check-outcome` retargeted, not retired (+ a latent bug fixed)

These verbs are invoked by **no** command `main.md` today (manual/future use; only tests reference them). Keep them and retarget their path expectations to the new layout.

While retargeting, fix the latent md-append bug in `research_helper append-outcome` (`_research/_cmds_handoff.py:287-289`): it joins `Path(handoff_path).parent / research_path`, producing `research/<date>-<slug>/research/<date>-<slug>.md` — a path that never exists — so the md append silently no-ops. Under the new layout the report IS the handoff's sibling, so the join becomes trivially correct; fix it and add the test that would have caught it.

### D5 — `/specify` loses NNN allocation + branch creation, gains feature-dir RESOLUTION

The Phase 0.4 gate transforms from *"a handoff exists somewhere"* to *"a feature dir exists that contains an intake handoff (`research-handoff.json` or `discover-handoff.json`) and does not yet contain `spec.md`"*. `/specify` resolves that dir (most recent by handoff mtime; ask the user when several are pending) and writes `spec.md` into it.

The `cold` pick survives with narrowed meaning: it means **"do not import the handoff's content into the spec"**, NOT "no feature dir". A cold `/specify` still writes into the resolved dir.

`/specify` **keeps** its branch-creation call as an **idempotent fallback guard**: if the session is still on the default branch when `/specify` runs (e.g. an intake run that predates this change, or a branch the user switched away from), create the branch then. This is a code fallback for a real state, not a discipline escape hatch — the normal path is that intake already created it and `create-branch`'s existing non-default-branch arm emits its informational comment and skips.

### D6 — Repeat intake on the same feature = attach mode, overwrite in place

A `/grill` RE-ENTER-UPSTREAM seed (`target_stage` = `research` or `discovery`) re-runs intake FOR AN EXISTING feature. The seed's own location (`specs/NNN-slug/grill-seed.json`) identifies the feature dir, so the run **skips allocation and branch creation** and **overwrites** `research-report.md` / `research-handoff.json` (or the discover pair) in place. The superseded version is preserved by the per-step git commits — no dated-filename proliferation.

### D7 — Unify the two lane layouts

Research's dir-per-run + flat-sibling-md shape and discover's all-flat shape collapse into one identical shape (D2 names). Every consumer glob simplifies to `specs/*/…`.

### D8 — Tier-1.5 probe-script rides scratch mid-run

The probe-script (today written mid-run to `research/<date>-<slug>/probe-script.*` — `research/main.md:789-806`, default at `_probe_tier.py:173`) is written to a **scratch** location during the run (`${TMPDIR:-/tmp}/forge-research/`, mirroring the `/audit` scratch pattern) and **copied** into `specs/NNN-slug/probe-script.<ext>` at finalize when the run saves. A dead-end run leaves it in scratch only, which is the intended D1 consequence.

Tier-1 probe TESTS (`tests/research/<slug>.probe<ext>`, `_probe_tier.py:169`) live in the consumer's own tests tree and are **UNCHANGED**.

### D9 — Structural bonus fixes (document, do not build separately)

The relocation eliminates, by construction: (a) the double-import hole; (b) the foreign-directory write-back; (c) the asymmetric layouts (= D7); (d) absolute-path provenance.

**(d) is decided, not merely enabled:** `source.handoff_path` (specify state) and `Provenance.upstream_handoff_path` (specify→plan handoff) become **install-root-relative** paths — e.g. `specs/001-x/research-handoff.json` — consistent with `research_path` / `report_path`, which are already root-relative strings. `plan_helper render-plan-seeds` resolves them against the install root (cwd) and **keeps its existing absolute-path tolerance** so pre-migration handoffs still resolve (they do, because D3 never deletes the old files).

Each of (a)–(d) is a consequence of the move, not a separate work item. No phase may claim one as its headline deliverable; every phase must avoid *re-introducing* one.

## Honest scope statements

- **This does not add a spec_path guard.** D9(a) makes double-import structurally impossible for NEW intake; no defensive check is added, so a hand-crafted or copied handoff could still be imported twice. Not covered by design.
- **This does not migrate existing consumer installs.** D3 is a clean cut. A consumer mid-feature at the moment of upgrade (intake done, `/specify` not yet run) will find their old-layout handoff invisible to the new `find-handoffs` and must re-run intake. Call this out in `CHANGELOG.md`.
- **`/research` and `/discover` stop being purely additive to the working tree.** They remain read-only *on source code*, but they now allocate a directory and create a git branch. Every doc that says "read-only" must be re-read for accuracy in Phase 6 — "read-only — does not modify code" stays true; any phrasing implying no repo mutation does not.
- **The old prefix-list entries are kept, not cleaned.** Legacy `research` / `discover` entries in lint-ignore / hygiene / isolation lists stay so old installs keep behaving; `specs` already covers the new layout. This is deliberate dead-but-harmless configuration, documented at each site.

## Open questions (resolve at the named phase — none block Phase 1's start)

- **OQ-1 — Home for the allocation substrate.** Shared module vs a `specify_helper` verb the intake orchestrators shell out to. **Recommend the shared module**: relocate `_next_spec_number` into `src/devforge/lib/_shared/` and expose thin verbs from `research_helper` / `discover_helper` / `specify_helper` over the one implementation — the exact precedent set by `_shared/feature_scope.py` (extracted from `_review/`, re-imported by `/review`, `/verify`, `/summarize`, `/finalize`). A cross-helper shell-out would make one command's helper a runtime dependency of another's, which nothing in the framework does today. Resolve at Phase 1.
- **OQ-2 — Does `find-handoffs` keep its mtime window?** The current 7-day window exists to avoid resurrecting a stale intake. Under D5 the discovery predicate is structural and precise (*handoff present AND `spec.md` absent*), so a window would now BLOCK `/specify` on a legitimately paused 8-day-old feature. **Recommend**: drop the window as a *filter*, keep mtime only as the *ordering* key for the most-recent pick. Resolve at Phase 4.
- **OQ-3 — Seedless repeat intake.** D6 covers the seed-driven attach case. What should a seedless re-run of `/research` on the same topic do? **Recommend v1**: allocate a NEW feature dir (current behavior in spirit — a new dated run was a new artifact) and say so in the run's output, so the user can delete it. Do not build topic-similarity matching. Resolve at Phase 2.
- **OQ-4 — Slug collision.** Two features can legitimately want the same slug (`NNN` differs, so no path collision), but a same-slug adjacent dir is confusing. **Recommend**: allow it — `NNN` is the identity, the slug is a label. Resolve at Phase 1 while writing the allocation verb's tests.
- **OQ-5 — Research slug source after the move.** `_RESEARCH_PATH_SLUG_RE` parses the slug out of the old dated path. **Recommend**: stop parsing paths — derive from the allocated feature dir name (authoritative, cannot drift) and drop the regex, converging research onto discover's `intent.topic_slug` posture. Resolve at Phase 4.

## Phases

Every `main.md` / agent-md edit routes through **instruction-author → instruction-reviewer**, plus **claude-code-guide** (these files ship into a consumer's `.claude/`). Every helper change routes through **python-engineer → python-reviewer**, test-first, with tests written and run in the same turn. No phase is exempt.

Test files are named per-phase rather than in one bulk phase — roughly 29 test files pin the old layouts, and each belongs with the code it pins.

### Phase 0 — Decision record — ✅ DONE 2026-08-05

D1–D9 above are maintainer-ratified. There is no open ratification gate; Phase 1 may start.

**Verify**: D1–D9 are recorded in this file with their rationale, and no phase below contradicts one.

### Phase 1 — Shared allocation substrate

Relocate `_next_spec_number` out of `_specify/_cmds_handoff.py` into a shared module (per OQ-1) and build an **allocate-feature-dir** capability on top of it, callable by all three helpers:

- Given a confirmed slug, compute the next `NNN`, create `specs/NNN-slug/`, and report the allocated path + number on stdout. Idempotent when handed an existing dir (the D6 attach path calls it with the dir already known, or bypasses it entirely — decide while writing the verb).
- Expose branch creation for the intake lanes, preserving all three arms of the existing `create-branch` semantics (default branch → emit `git checkout -b spec/NNN-<slug>`; already on a `spec/*` branch → skip; other non-default branch → informational comment, skip).
- Keep `_specify`'s call sites working (D5's fallback guard needs both capabilities).
- Wrapper mode: resolve the install root, never the source root.

Loop: **python-engineer → python-reviewer**. Tests: new tests for the shared module + allocation verb (fresh repo → 001; existing `specs/003-*` → 004; non-`NNN` dirs ignored; slug collision per OQ-4; wrapper-root resolution); update `tests/lib/test_specify_helper.py` and `tests/lib/_specify/*` for the relocated import.

**Verify**: `_next_spec_number` has exactly one implementation (grep shows one `def`); `research_helper`, `discover_helper`, and `specify_helper` can each allocate a feature dir and create a branch; the specify-side tests pass unchanged in behavior; new tests cover the three branch arms.

### Phase 2 — `/research` producer

Helper (python-engineer → python-reviewer):
- `_handoff_build.py:410-414` `research_path` default → `specs/NNN-slug/research-report.md` shape.
- `_cmds_handoff.py:138-147` finalize-handoff writes `research-handoff.json` into the feature dir; decide whether `--emit-handoff-json` stays REQUIRED (`_cli.py:259-261`) or gains a feature-dir-derived default.
- `_probe_tier.py:173` tier-1.5 default → the `${TMPDIR:-/tmp}/forge-research/` scratch path (D8); `:169` tier-1 test path UNCHANGED.
- `_cmds_phase2.py:143` Next-Step literal re-worded to the new report path.

Command spec (instruction-author → instruction-reviewer + claude-code-guide) — `src/commands/research/main.md`:
- Rewrite the save/finalize/commit block (`:971-1008`) into the D1 ordering: confirm save → confirm slug → allocate → branch → write report + handoff (+ copy the probe-script per D8) → `commit-artifacts` with the new path-set.
- **Slug confirmation adds no new question** (D1): extend the EXISTING save-prompt `AskUserQuestion` to also display the proposed feature name (2–4 words, kebab-case, from `topic_slug`), relying on the tool's built-in "Other" free-text option as the override. Do not author a second question — the AskUserQuestion contract's option ceiling and the single-line question rule both apply to the one prompt.
- Add the D6 attach-mode branch to the grill-seed re-entry block (`:122-134`): a seed at `specs/NNN-slug/grill-seed.json` means skip allocation + branch, overwrite in place.
- Update the declared outputs at `:17-18` and the scratch note.
- State the OQ-3 seedless-re-run behavior explicitly.

Tests: `tests/lib/test_research_helper.py`, `test_research_handoff_schema.py`, `test_research_design_anchor.py`.

**Verify**:
- A `/research` run that saves produces `specs/NNN-slug/research-report.md` + `research-handoff.json` (+ `probe-script.<ext>` when tier-1.5 fired) and nothing under `research/`; a run that terminates "not a bug" creates no `specs/` dir.
- The save prompt shows the proposed feature name and accepts a free-text override; no second question was added.
- `grep -rn 'research/{' src/devforge/lib/_research/*.py` returns no surviving path default. **Use this pattern, not `research/{date}`** — two of the three defaults build their paths with positional placeholders (`_handoff_build.py:414` and `_probe_tier.py:173` use `{0}`/`{1}`), so a `{date}`-literal grep matches only `_cmds_phase2.py:143` and would pass while both important defaults are still stale.
- Checklist assertion — each of the three call sites was individually edited and can be named: (1) `_handoff_build.py` `research_path` default, (2) `_probe_tier.py` tier-1.5 probe-script default, (3) `_cmds_phase2.py` Next-Step literal.
- Reviewer loops clean.

### Phase 3 — `/discover` producer

Same shape as Phase 2 for the greenfield lane.

Helper (python-engineer → python-reviewer):
- `_handoff_build.py:500-504`, `:598` `report_path` default → `specs/NNN-slug/discovery-report.md`.
- `_cmds_handoff.py:86-101` + `_cli.py:584-592` finalize-handoff default → `specs/NNN-slug/discover-handoff.json`.
- `handoff_schema.py:989`, `:1014` — `report_path` stays required non-empty; confirm the new value satisfies it.
- `_cmds_design.py:316` Next-Step literal.

Command spec (instruction-author → instruction-reviewer + claude-code-guide) — `src/commands/discover/main.md`:
- **Move `finalize-handoff` (Phase 4.0, `:572-580`) to AFTER the save confirmation (`### Ask to save`, `:582-586`)** per D1, so a `skip` leaves no orphaned handoff. This re-orders a numbered phase — renumber or re-title carefully and check every internal cross-reference to Phase 4.0.
- Rewrite the save/commit block (`:588-600`) into the D1 ordering.
- **Slug confirmation folds into the existing `### Ask to save` prompt** (D1) — that one `AskUserQuestion` also displays the proposed feature name, with the built-in "Other" as the override. No second question.
- Add the D6 attach-mode branch to the grill-seed block (`:140-152`).
- Update declared outputs `:18-19` and the scratch note.

Tests: `tests/lib/test_discover_handoff_cli.py`, `test_discover_handoff_build.py`, `test_discover_handoff_schema.py`, `test_discover_topic.py`, `test_discover_state.py`, `test_discover_design_anchor.py`.

**Verify**: a saving `/discover` run produces the two new files in one feature dir and nothing under `discover/`; a `skip` at the save prompt leaves NO handoff anywhere (the wart is gone); the save prompt shows the proposed feature name with a free-text override and no second question was added; no `main.md` text still references the old Phase-4.0 position; reviewer loops clean.

### Phase 4 — `/specify` consumer

**Shipping stance — Phases 1–4 are a single atomic shipping unit.** Phase 2/3's producer change must NEVER land in the working tree without Phase 4's consumer change in the same change-set, because `/specify`'s Phase 0.4 gate (`find-handoffs --require`, exit 2, no override) would find zero handoffs and block every future feature. Phases 5–8 may land in later sessions.

Helper (python-engineer → python-reviewer) — `src/devforge/lib/_specify/`:
- `find-handoffs` (`_cmds_handoff.py:730-880`): replace the `os.walk` + `iterdir` pair with one glob over `specs/*/research-handoff.json` and `specs/*/discover-handoff.json`, filtered to dirs with no `spec.md` (D5); resolve OQ-2 on the mtime window; rewrite the `--require` exit-2 BLOCKED message and the CLI help (`_cli.py:717`, `:723-728`).
- `import-handoff` (`:374-430`, `:433-547`, `:591-722`): `future_spec_path` becomes the dir the handoff already sits in; the `spec_path` back-fill becomes a sibling write; research slug derivation per OQ-5; `source.handoff_path` (`:510` / `:683`) becomes **install-root-relative** per D9(d) — not absolute — matching the already-root-relative `research_path` / `report_path` strings.
- Remove NNN allocation + branch creation from the `/specify` main path, keeping both reachable as the D5 fallback.
- `_topic.py:59-72` `source_origin_for_path`: the new intake files live under `specs/`, so prefix-only dispatch would tag them `prior_spec`. Switch to filename-aware dispatch (`specs/*/research-report.md` → research, `specs/*/discovery-report.md` → discover, other `specs/` paths → prior_spec). **This is the single highest-risk edit in the plan** — a silent mis-tag degrades corpus grouping without failing anything.
- `_cmds_phase01.py:269-278` `_group_for_path` and `_schema.py:270-278` render order: align with the new origins.
- `_schema.py:257-266` greenfield table.

Command spec (instruction-author → instruction-reviewer + claude-code-guide) — `src/commands/specify/main.md`:
- Phase 0.4 gate + pick flow + `cold` semantics (`:99-115`) rewritten to D5's dir-resolution framing.
- Phase 0.2 branch decision (`:57-74`) reframed as the fallback guard; Phase 4 branch block (`:507-521`) likewise.
- Phase 1 corpus reads (`:193-201`): `ls research/` / `ls discover/` → read the resolved feature dir.
- Spec-type pre-seeding path-prefix tests (`:394`, `:416-418`) and the greenfield doc (`:444`).
- Declared outputs (`:18-19`) reconciled — branch creation is no longer normally `/specify`'s.

Tests: `tests/lib/test_specify_helper.py`, `tests/lib/_specify/test_find_handoffs_require.py`, `test_finalize_handoff.py`, `test_handoff_schema.py`.

**Verify**:
- `find-handoffs` finds both lanes from one glob and ignores dirs that already contain `spec.md`; `--require` exits 2 with a message naming the new locations.
- `import-handoff` writes `spec_path` to a sibling and computes no new `NNN`.
- A `/specify` run on a feature dir whose intake already branched creates no second branch; a `/specify` run on the default branch (fallback case) does create it.
- `source_origin_for_path` tags `specs/NNN-x/research-report.md` as research and `specs/NNN-x/spec.md` as prior_spec — assert both directions in a test.
- A freshly produced specify→plan handoff carries an install-root-relative `provenance.upstream_handoff_path` (e.g. `specs/001-x/research-handoff.json`, no leading `/`) and a root-relative `source.handoff_path` — assert on the written JSON, per D9(d).
- Phases 1–4 land together (shipping stance above): the same change-set contains the producer defaults AND the consumer glob.

### Phase 5 — Downstream consumers

- **Provenance (D9d)** — `plan_helper` `read-specify-handoff` (`plan_helper.py:1050-1101`) + `render-plan-seeds` (`:1390-1470`) + `src/commands/plan/main.md:60-80`: resolve an install-root-relative `upstream_handoff_path` against the install root (cwd), while KEEPING absolute-path tolerance so pre-migration handoffs still resolve (D3 — the old files persist). The existing dangling-path exit-2 behavior is unchanged.
- `src/commands/plan/main.md:199` — the skip-with-reference prose ("an existing file under `research/`") re-points to `specs/[feature]/research-report.md`.
- **`/pr-review`** — `_pr_review/_handoff_import.py:88-119`, `:315-330` `_scan_research_dir` re-points to `specs/*/research-handoff.json` (clean cut per D3 — no dual scan); `_pr_review/_cli.py:317-320`; `src/commands/pr-review/main.md:192`.
- **`append-outcome` / `check-outcome` (D4)** — retarget path expectations in `_research/_cmds_handoff.py:204-340` (+ `_cli.py:814-852`) and `_discover/_cmds_handoff.py:180-367`; **fix the md-append join bug** at `_research/_cmds_handoff.py:287-289` and simplify the discover two-candidate probe (`:340-360`) now that the report is always the handoff's sibling.
- `src/agents/devils-advocate.md:33` — re-read the recon-dossier wording; edit only if it asserts a location.

Loops: python-engineer → python-reviewer for the helper edits; instruction-author → instruction-reviewer + claude-code-guide for `plan/main.md`, `pr-review/main.md`, and any `devils-advocate.md` touch.

Tests: `tests/lib/test_plan_helper.py`, `test_plan_handoff.py`, `test_plan_stakes_hint.py`, `tests/lib/_pr_review/*` (4 files), plus a new regression test asserting `append-outcome` actually appends to the report md (the D4 bug).

**Verify**: `append-outcome` appends to a real file and a test asserts the file's post-content (not just exit 0); `/pr-review`'s scan finds a new-layout handoff; `render-plan-seeds` resolves a new-layout provenance path; no downstream doc still points readers at `research/`.

### Phase 6 — Prefix-list sweep + docs reconcile

Per-site decisions, each documented **inline at the site**:
- `_configure/_lint_ignore.py:56-64` + `configure/main.md:402`, `:424` — KEEP legacy `research` / `discover` entries (old installs still have the dirs); note that `specs` already covers the new layout.
- `_verify/_hygiene.py:157-160` — same disposition.
- `_implement/_cmds_verify.py:165-175` `ISOLATION_ARTIFACTS` — same; also note that its pre-existing asymmetry (`research` present, `discover` absent) is mooted by the clean cut rather than fixed.

Docs:
- `src/devforge/storage-rules.md` — `:7-45` directory structure (drop the top-level research/discover trees for new work; add the D2 files to the `specs/NNN-feature-name/` tree), `:88` FEATURE-SCOPED class wording, `:94` scratch-vs-record (add the `specs/NNN/research-report.md` vs `.devforge/research-report.json` pair), `:180-181` File Lifecycle.
- `src/CLAUDE.md` — the `/research`, `/discover`, `/specify` Workflow one-liners; the matching Command Details entries; and the `## Artifact Storage` block (which currently opens with the `research/` and `discover/` trees). Re-check the "Read-only" phrasing against the honest-scope note above.
- `CHANGELOG.md` — the relocation, plus the D3 no-migration note for consumers mid-feature at upgrade.
- Repo-root `CLAUDE.md` — add the plan-68 entry to the active-plans list (and to the "Where to find what" pipeline-handoff rows, which currently name `research/<date>-<slug>/handoff.json` and `discover/<date>-<slug>.handoff.json`).

Loop: instruction-author → instruction-reviewer + claude-code-guide for `src/CLAUDE.md` and `configure/main.md`.

**Verify**: every prefix-list site carries an inline note stating why its legacy entry stays; no doc describes the top-level dirs as where new intake lands; the repo-root CLAUDE.md handoff rows name the new paths.

### Phase 7 — Full-suite + cross-reference sweep

- Run the full test suite; zero regressions.
- `grep -rn "research/" src/ scripts/` and `grep -rn "discover/" src/ scripts/` — every hit must be either (a) updated to the new layout, (b) an intentionally-retained legacy prefix-list entry with its inline note, or (c) prose about the `/research` / `/discover` *commands* rather than the directories. Enumerate the surviving hits in this plan's status line so a future session does not re-litigate them.
- `grep -rn "handoff.json" src/` — confirm no reader conflates the specify→plan `handoff.json` with the two new intake handoff names.
- Run `python3 scripts/verify-agent-reachability.py` (plan 41's standing gate) — no agent should be affected, so a non-zero exit means something else broke.
- Run the emitter/install ride and confirm no `{{` leaks and both intake commands still install.

**Verify**: full suite green; the two greps produce only classified hits; reachability gate green; install ride clean.

### Phase 8 — Consumer / testForge20 e2e (USER-DRIVEN, HARD GATE)

On a fresh consumer install:
1. Run `/research` on a real topic through to save. Confirm `specs/NNN-slug/` was created at finalize (not earlier), the branch `spec/NNN-<slug>` exists, both artifacts are inside the dir, and `git status` is clean afterwards.
2. Run `/research` on a topic that terminates "not a bug". Confirm NO `specs/` dir and NO branch were created.
3. Run `/specify` → confirm it resolves the existing dir, creates no second branch, writes `spec.md` beside the intake artifacts, and back-fills `spec_path` in the sibling handoff.
4. Continue `/plan` → confirm the provenance follow resolves and the upstream seeds render.
5. Repeat 1+3 through the `/discover` lane, including a `skip` at the save prompt (confirm no orphaned handoff).
6. Run `/grill` to a RE-ENTER-UPSTREAM disposition with `target_stage: research`, then re-run `/research` — confirm D6 attach mode: no new dir, no new branch, artifacts overwritten in place, superseded version recoverable from git history.

**Verify**: all six scenarios behave as described; a final `/finalize` squash contains the intake artifacts in the feature commit.

## Dependencies + related

- **Plan 37 (per-step artifact commit)** — supplies `artifact_helper commit-artifacts`, which every intake commit path-set in this plan reuses unchanged. The relocation moves *what* is committed, not *how*.
- **Plan 65 (status-flip artifact commit)** — same "commit what you write or mutate" discipline; its `/plan` + `/breakdown` path-sets are untouched here.
- **Plan 49 (`.devforge/` runtime-state disposition)** — owns the EPHEMERAL/VERSIONED/FEATURE-SCOPED classes this plan's new files join as FEATURE-SCOPED; owns the scratch-vs-record trap wording D2 extends.
- **Plan 23 / 36 / 39 (grill re-entry seeds)** — own the seed shape D6's attach mode keys off; this plan adds no new `target_stage` and changes no seed schema.
- **Plan 53 (design anchor first-class)** — the "park once, read in place" precedent that makes a feature-dir-anchored artifact the framework's normal shape rather than a novelty.
- **Plan 67 (caller-enumeration carry)** — currently in flight on the research handoff's typed fields; its `handoff_schema.py` work and this plan's path work touch the same package. Sequence them, or expect a merge conflict in `_research/_handoff_build.py`.

## Context for next session

- **Phases 1–4 are a single atomic shipping unit.** Phase 2/3's producer change must never land in the working tree without Phase 4's consumer change in the same change-set, because `/specify`'s Phase 0.4 gate (`find-handoffs --require`, exit 2, no override) would find zero handoffs and block every future feature — and D3 forecloses a dual-glob stopgap. Phases 5–8 may land in later sessions.
- **The trap is scope creep into a migration tool.** D3 is a clean cut: no dual-glob readers, no back-fill script, no compatibility shim. If a phase starts growing a "read old layout too" branch, it has left the plan.
- **Allocation timing is the load-bearing decision.** D1 puts it at *finalize*, after the save AND slug confirmations. A future session that "simplifies" by allocating at run start re-introduces dead-end litter and breaks the zero-footprint guarantee for abandoned investigations.
- **`_topic.py`'s `source_origin_for_path` is the quiet landmine** (Phase 4). Once intake artifacts live under `specs/`, prefix-only dispatch tags them `prior_spec` and nothing fails loudly — the corpus grouping just silently degrades. It needs filename-aware dispatch and a test asserting both directions.
- **The `discovery-` / `discover-` stem asymmetry in D2 is deliberate.** Do not normalize it.
- **`/specify` keeps branch creation** as a fallback (D5) — that is not leftover code to delete.
- **`append-outcome` is called by no command** (D4). Retargeting it is correctness hygiene, not a wiring task; do not add a caller as part of this plan.
- Per-phase agent loops are mandatory: `main.md` / agent-md → instruction-author → instruction-reviewer + claude-code-guide; helpers → python-engineer → python-reviewer, test-first.

## When resuming work

1. Read this file in full. D1–D9 are ratified — do not re-litigate them; resolve OQ-1..OQ-5 at their named phases.
2. Re-verify the `file:line` refs for the phase you are about to execute (the sweep is dated 2026-08-05; line numbers drift). Where this plan says "locate at build time", locate — do not guess.
3. Check whether plan 67's `_research` handoff work has landed; if it is still in flight, sequence Phase 2 after it.
4. Execute phases in order — 1 (substrate) gates 2 and 3; 2+3 (producers) gate 4 (consumer); 4 gates 5. **Land 1–4 as one change-set** (shipping stance in Phase 4) — a producer-only landing bricks `/specify`.
5. Phases 6 and 7 close the sweep; hand Phase 8 to the user as a hard gate.
