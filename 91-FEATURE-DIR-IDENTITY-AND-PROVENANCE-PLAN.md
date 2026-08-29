# 91 — Feature-directory identity + artifact provenance

**Status**: **PHASES 1 AND 1b BUILT** — Phase 1 on **2026-08-28** (18 commits), Phase 1b on **2026-08-29** (7 commits), all on `develop-2.0-init`; see each phase's own build record. The resolution accessor landed in `_shared/feature_alloc.py` and all six depth-1 resolvers migrated onto it; the shared discovery verb `artifact_helper find-feature-artifacts` then closed the discovery-glob class across eleven command specs. The prose sweep took `specs/` in command specs from **388 occurrences across 26 files → 69 across 17 (Phase 1) → 45 across 14 (Phase 1b)**, every survivor classified. **Build-verified only — NOT consumer-validated**; nothing has been run against a real install. ⚠ **Phase 1b's build also fixed a REGRESSION Phase 1 introduced** (`9bf49aa`) — source-origin tagging broke for absolute paths, no test caught it, and Phase 3's discover pre-seed could not have fired; see Phase 1b's build record and the dated correction in Phase 1's. PHASE 0 CLOSED 2026-08-28 — every item (D1–D9 + OQ-1–OQ-8) ratified AS RECOMMENDED, D1 = (a); D4 and D6 ratified BY DIRECTIVE with the deliberation they demanded NOT performed. **BOTH deliberations were performed 2026-08-29 and BOTH decisions UPHELD, so NO deliberation is outstanding: D4 narrowly and on its own merits, handing two obligations to Phase 2; D6 on a WEAKER footing — it stands because D2 and D3 ENTAIL it, not because it was argued on its merits — handing one obligation to Phase 3.** D4's closure is recorded in D4's ⚠ and in `## Phase 0 close record`; D6's is recorded in D6's ⚠ ONLY, and that section's two D6 lines still read `NOT performed` and are stale on that point. Phases 2–6 have not started.
**Created**: 2026-08-26
**Branch**: `develop-2.0-init`
**Origin**: maintainer design conversation 2026-08-26 (no incident, none claimed). Two problems raised together and deliberately kept separate below: *identity* (a feature directory's name carries no external meaning) and *volume* (a flat `specs/` accumulates unboundedly over a multi-year, multi-dev project).

---

## Why

Today a feature directory is `specs/NNN-<slug>/`, where `NNN` is a repo-local sequential counter allocated by scanning `specs/` (`_shared/feature_alloc.py`). Three consequences the maintainer named:

1. **`NNN` means nothing outside this repo.** The framework already knows about tickets — `_implement/_cmds_commit.py:162` scrapes `[A-Z]+-[0-9]+` out of a *source* branch in wrapper mode — but it never asks for one, so in standalone mode the ticket is unknown. `/devforge:finalize` cannot compose `[PROJ-123] - Description` there either, though for a separate reason: that format is gated on wrapper mode, not on knowing a ticket (see D5).
2. **A flat `specs/` becomes a junk pile.** At a realistic ~8 features/month over two years that is ~200 sibling directories.
3. **Provenance is git-only.** Once an artifact leaves the repository (a `spec.md` pasted into a PR description, a ticket comment, or the maintainer's Obsidian vault), the git metadata is gone and nothing in the document says who ran the command that produced it.

### The argument that shaped the design (recorded so it is not re-litigated)

An earlier candidate — keep `specs/` flat and have `/devforge:finalize` move completed features into `specs/archive/` — was **rejected** on the maintainer's objection, which is recorded here because it generalizes:

> Features that die mid-pipeline never reach `/devforge:finalize`. An archive driven by a terminal command therefore collects the *completed* work (which is already orderly) and leaves the *abandoned* work (the actual mess) in place. Any scheme where correct placement depends on a later action drifts, and abandoned work has no later action by definition.

The invariant adopted in its place, and binding on every decision below:

> **Placement is decided at creation time, by a mechanism that already has to run, and never changes afterwards.**

Intake allocation (`/devforge:research` / `/devforge:discover` Phase 4) is such a mechanism. A finalize-time move is not.

---

## What ships, and in what order

Three changes. The ordering is itself a ratification item (D1) because it is the difference between paying the prose cost once or twice.

| | Change | Layer |
|---|---|---|
| **F1** | The feature-directory path becomes **opaque**: the helper is the only author of the layout; command prose receives a path and never composes one. | Python + 388 prose occurrences |
| **F2** | Identity becomes the **ticket**; layout becomes `specs/YYYY/MM/TICKET/`; `REQUIRE_TICKET` gates intake. | Python (composition + six variable-depth resolvers) + intake prose |
| **F3** | A **`Run by:`** provenance line on the artifacts that travel outside the repository. | Python (2 renderers) + prose (2 artifacts) |

F1 is the enabling refactor: it exists so that F2 — and the *next* layout change after F2, which there will be — is paid inside the helper plus its resolvers instead of across 388 prose occurrences. It does **not** make the resolver work cheap; see D1 and Phase 3.

⚠ **F1 shipped 2026-08-28 and its row above states a GOAL, not an achieved state.** The row's *"Python + 388 prose occurrences"* is F1's cost as scoped and as paid — the count is history, not a live figure. Two clauses of F1's own description came out qualified by the build and are recorded where they bite rather than here: **prose does not compose a path, except for the discovery globs the orchestrator runs itself** (deferred to Phase 1b, inventoried there), and **the helper is not the only author of the layout** — `/devforge:specify`'s genuine-fallback arm still creates the directory with a bare `mkdir -p` and no helper verb exists for it (Phase 3's structural facts). Neither qualification reopens D1; both are stated so Phase 3 does not assume the row is literally true.

⚠ **AMENDED 2026-08-29 — the FIRST qualification is closed as a layout concern and survives only in a narrowed form; the SECOND is untouched.** Phase 1b moved the discovery-glob class onto `artifact_helper find-feature-artifacts` in all eleven consuming command specs, so no command spec composes a `specs/`-rooted discovery path any more. **One orchestrator-run glob deliberately remains** — `/devforge:specify` Phase 0.5's `<feature_dir>/*-seed.json` — and it is **not** a Phase-3 hazard: it is rooted at the opaque `<feature_dir>` token, not at `specs/`, so it carries no depth assumption to break. It stayed a glob because the verb would over-search, not because it was missed; Phase 1b's **Verify** records the reason in full. The `mkdir -p` qualification is unchanged and still bites at Phase 3.

---

## Verified ground truth

Everything below was originally read from the tree on **2026-08-26** and **re-verified on 2026-08-27**, after plans 85, 88, 89 and 90 shipped. Cited so a future session does not re-derive it, and does not trust it blindly either — re-grep before acting.

Re-verified 2026-08-27 and found **UNCHANGED**, so a future session need not re-check them:

- `_shared/feature_alloc.py:99` / `:101` / `:122` / `:125` — all four still exact.
- All six depth-1 resolvers still at their cited lines.
- `_specify/_render.py:135` — `**Author**: Claude + User` still present.
- `_research/_render.py:51-54` — unchanged.
- The `is_wrapper` gate **logic** is unchanged (the standalone arm still assigns `ticket_id = ""`), so D5's known gap stands exactly as written — only its line citations moved, and they are corrected in place below.
- Plan 90's e2e artifacts land in the project's own test tree — *"a dedicated e2e directory that the package's ordinary test command does not match"* (`src/commands/breakdown/main.md:457`) — **not** under `specs/`. This plan's `specs/` surface did not grow from plan 90.

What *did* move: the prose-occurrence counts (386 → 388, 296 → 298 lines, 25 → 26 files) and several `_implement/_cmds_commit.py` / `_configure/_render.py` / `_shared/feature_alloc.py` / `plan_helper.py` line numbers. Every one of those is corrected in place. On 2026-08-27 every `file:line` citation in this document was opened and confirmed to say what the citing sentence claims, and the per-shape breakdown below was re-taken in full. ⚠ Two derived figures were **not** re-taken and remain 2026-08-26 readings: the "20 modules" header-line count and the 86-line docstring length.

### The layout is authored in two places at once

- `_shared/feature_alloc.py:101` — `SPECS_ROOT_DEFAULT = "specs"`.
- `_shared/feature_alloc.py:122` — `SPEC_NUMBER_DIR_RE = re.compile(r"^(\d{3})-(.+)$")`. **Exactly three digits**, deliberately not widened; pinned by `tests/lib/_shared/test_feature_alloc.py::test_non_nnn_dirs_ignored`.
- `_shared/feature_alloc.py:99` — `FEATURE_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+){1,3}$")` — 2–4 lowercase kebab segments.
- `_shared/feature_alloc.py:125` — `_SPEC_BRANCH_PREFIX = "spec/"`.
- `allocate_feature_dir` **already returns the full path** (`"path"`, alongside `number` / `formatted_number` / `slug` / `dirname` / `created`).

And yet the command specs rebuild that same path by hand. Raw occurrence counts across `src/commands/**/*.md`, first taken 2026-08-26 and recounted 2026-08-27 with one consistent method — `grep -rho 'specs/' src/commands --include="*.md" | wc -l`:

```
117 × specs/<NNN-slug>        28 × specs/<feature>       12 × specs/<NNN>-<feature-name>
104 × specs/[feature]         27 × specs/<dirname>        8 × specs/<NNN>-<slug>
 32 × specs/                  24 × specs/*                6 × specs/<NNN>-<feature>
 21 × specs/NNN-*             + smaller variants
```

The breakdown above was **re-taken on 2026-08-27** with the same method as the total, so every row is a measurement. Two named shapes moved between the readings — `specs/[feature]` 100 → 104 and `specs/NNN-*` 20 → 21; the other eight are unchanged. The named shapes sum to 379 and the smaller variants carry 9, totalling 388.

**388 raw occurrences across 298 matching lines in 26 command-spec files, in at least nine different spellings.** This — not directory depth — is what makes any layout change expensive. Phase 0 re-derives the figure with the command above; counting *lines* instead of occurrences yields 298 and is not the number this plan is scoped against.

⚠ The counts move as the tree moves, and did between the two readings above: **386 / 296 / 25 on 2026-08-26 → 388 / 298 / 26 on 2026-08-27.** The 26th file is `src/commands/fix/references/triage.md`, added by plan 88's cold-fix lane. Treat the figure as an order of magnitude with a re-derivable method attached, never as a constant.

⚠ **Every figure in this subsection is now a PRE-SWEEP reading.** It is preserved unedited as the baseline Phase 1 was scoped and argued against — not rewritten — under the same discipline `## Phase 0 close record` applies to the pre-close text. Phase 1 shipped 2026-08-28 and the post-sweep figure is **69 occurrences across 17 files**. The nine-spelling breakdown above is therefore a list of what the sweep **retired**, not of what survives; do not read a row of it as current, and do not use the 388 figure to argue the cost of anything after 2026-08-28. What survives is classified in four named classes in Phase 1's amended **Verify**, and the largest of those classes is inventoried file-and-line in Phase 1b.

⚠ **AMENDED 2026-08-29 — the post-sweep figure moved again.** Phase 1b shipped the same-week follow-on and the current reading, re-derived with the identical command on **2026-08-29**, is **45 occurrences across 14 files**. The full trajectory is therefore **388 / 26 → 69 / 17 (Phase 1) → 45 / 14 (Phase 1b)**. Class **(b)** — the discovery-glob class, the largest survivor group and the one this note previously pointed at Phase 1b to inventory — is **closed**; what remains is classes (a), (c) and (d) plus the one deliberate class-(b) survivor Phase 1b's **Verify** names. Both earlier figures are history: re-derive, never quote.

### Resolution is uniformly depth-1 — `Path.iterdir()` at four sites, `os.listdir()` at two

Every consumer assumes a feature directory is an immediate child of `specs/`. The depth-1 assumption is uniform across all six; the API is not:

- `plan_helper.py:304` — `_glob_specs`
- `breakdown_helper.py:346` — `_glob_plans`
- `_implement/_cmds_resolve.py:114` — `_glob_feature_dirs`, sorted by `_feature_sort_key` (`^(\d+)`, falling back to `2**31`)
- `_specify/_cmds_handoff.py:1014` — `find-handoffs`'s `sorted(specs_root.iterdir())`
- `_grill/_scope.py:105` — `resolve_target_feature`'s `os.listdir(specs_root)`; the NNN filter `_NNN_RE.match(entry)` sits at `:114` (`_NNN_RE = re.compile(r"^(\d+)")` at `:46`)
- `_pr_review/_handoff_import.py:157` — `os.listdir(specs_dir)`

### Provenance

- `_specify/_render.py:135` — `out.append("**Author**: Claude + User")`. **This is the only `**Author**` literal in production renderer code (`src/`)**, and it is a hardcoded constant that names nobody. (The string also appears in test fixtures and assertions under `tests/` and once in `done-plans/`; none of those render anything.) F3 is therefore *replacing a field that already lies*, not adding a new one — at least for `spec.md`.
- `_specify/_render.py:132-134` — the surrounding header: `**Date**:`, `**Status**:`, `**Design source**:`.
- `_research/_render.py:51-54` — `**Date**:`, `**Topic**:`, `**Mode**:`, `**Verdict**:`. No author field.
- `plan.md` and `summary.md` are **LLM-authored prose** — no Python renders either one. The two differ downstream: `plan.md` is *parsed* by `plan_helper.py` (`:83` documents the `finalize-handoff` verb, `:2135` is `cmd_finalize_handoff`), while `summary.md` is neither rendered nor parsed by any Python in this repository. A stamp on either is an instruction change, not Python.
- **Zero** reads of `git config user.name` anywhere in `src/devforge/lib/`. There is no identity source in the framework today.
- `_configure/_render.py:148-150` — `COMMIT_ATTRIBUTION` is a *derived* config key, emitted only when `ai_attribution == "Yes"`; those three lines are the gate itself (`ai_attribution = cfg_state.get("ai_attribution")` / `if ai_attribution == "Yes":`). Its supporting sites: `:54` lists the key in the emitted key order, `:82` is the explanatory comment, `:84` defines `_COMMIT_ATTRIBUTION_YES`. The framework already asks the operator whether attribution may be written into files.
- **20 modules** write `**Status**:` / `**Created**:` / `**Date**:` header lines. There is **no shared header composer**. "Every artifact carries a label" would therefore be 20 touch points plus a test each.

### Adjacent facts that constrain this plan

- The research / specify / discover handoff schemas carry **no** `feature_dir` or `path` key (grep-verified). The layout is not baked into the JSON contracts, so changing it does not stale a stored path. *Phase 0 re-confirms this before Phase 3 relies on it.*
- Plan 68 D3 set the precedent that legacy intake directories are **inert history — nothing migrates them**. This plan follows it (D6).
- Plan 68 D6 attach mode: a `/devforge:grill` RE-ENTER-UPSTREAM seed reuses an existing feature directory and **skips allocation entirely**. Any allocation-time rule must therefore have an attach-mode arm that is a deliberate no-op.
- Plan 87 (artifact language guard) and plan 78 (test identifier scrub) both exist because artifacts are committed and this repository is public. F3 adds a real human name to committed files and must be weighed against that, not around it.
- Plan 88 (cold-fix bugs lane) is **CLOSED 2026-08-27 (build)** — Phases 0–4 complete 2026-08-26, Phase 5 consumer e2e deferred and **NOT run**. It owns `bugs/NNN-*.md`. Whether `REQUIRE_TICKET` reaches bug files is OQ-4; plan 88 changed no bug-file naming, so that recommendation stands as written.
- ⚠ **A legitimate feature-less command path now exists, and this plan's rules do not reach it.** Plan 88's cold lane — `/devforge:fix bugs/NNN-<slug>.md` — runs with **no feature directory at all**, by decision rather than omission: its D2 bypasses `/devforge:fix` PHASE 0.2 (feature resolution), PHASE 0.3 (`in-fix-window`) and PHASE 0.4 (`read-findings`), all three of which need a `--feature` a cold run does not have. Everything in this plan — F1's opaque path, F2's layout, D4's `REQUIRE_TICKET` gate — binds the **intake-allocated feature path only**. Phase 1's resolution accessor must therefore not be specified as though every caller holds a feature reference: a caller with none is a supported state, not an error path. This is a boundary statement; it invents no behaviour for the cold lane, and this plan changes none.

---

## Decisions to ratify (D1–D9)

D2, D3, D5, D7, D8 and D9 were argued and settled in the originating conversation; they are listed anyway because Phase 0 is where a decision becomes binding in this repository. **D1 is genuinely unanswered** and must be settled first — it changes the shape of every phase after it.

That leaves **D4 and D6**, which belong to neither bucket and must not be waved through by omission:

- **D4 was PARTIALLY argued.** The maintainer agreed to the `REQUIRE_TICKET`-as-per-install-policy-key *shape*. The tripwire break that shape carries (D4's ⚠) was never put to them as a decision, so D4 requires full Phase-0 deliberation.
- **D6 was NOT argued at all.** It retires `NNN` as the feature identity and never came up in the originating conversation. It requires full Phase-0 deliberation.

### D1 — Sequence: opaque path first, or layout first? — RATIFIED AS (a) BY DIRECTIVE 2026-08-28

- **(a) F1 first (RECOMMENDED).** Make the helper the sole author of the path, retire the 388 hand-composed occurrences, *then* change the layout inside the helper. Cost: the prose sweep is paid once, up front, before any user-visible behaviour changes.
- **(b) Layout first.** Ship `specs/YYYY/MM/TICKET/` directly. Cost: 388 prose occurrences edited now, and 388 again the next time the layout changes — and this conversation produced three candidate layouts in one sitting, so a next time should be assumed, not hoped against.

The whole argument for (a) is that **the prose sweep is paid once instead of twice**. It is not that (a) makes the layout switch cheap: under either ordering, Phase 3 still has to teach six resolvers a variable-depth walk that returns both the legacy and the new shape (see Phase 1's ⚠ and Phase 3). No ordering makes that work disappear, and this plan does not claim it does.

Recommendation (a). The counter-argument is honest and recorded: (a) delivers **nothing the maintainer asked for** in its first phase, and a refactor whose payoff is entirely in the next phase is the kind that gets abandoned half-done. If (a) is ratified, Phase 1 must therefore be independently valuable — it is: it removes a nine-spelling literal from 26 files, which is a real hallucination surface today regardless of any layout change.

⚠ Phases 1, 2 and 3 below are written for (a). Ratifying **(b)** requires restructuring Phases 1–3 *before* any build starts — this document provides no alternate structure for it. **DISCHARGED 2026-08-28** — (a) was ratified, so no restructure is owed and Phases 1, 2 and 3 stand exactly as written. Retained rather than deleted because it is the reason those three phases have the shape they do.

### D2 — Layout: `specs/YYYY/MM/TICKET/` — RATIFIED IN CONVERSATION 2026-08-26

Two levels of date, then the ticket. e.g. `specs/2026/08/PROJ-123/`.

Rejected alternatives and why, recorded so they are not revived without new evidence:

- **Week level (`2026/08/W35/`)** — rejected. The week number already determines the month, so `08/W35` encodes the month twice; ISO and US week numbering differ; weeks straddle month boundaries; and at ~2 features/week the bucket holds 1–3 entries, i.e. a three-level tree partitioning two items.
- **Single combined segment (`specs/2026-08/`)** — proposed and declined by the maintainer.
- **Flat + finalize-time archive** — rejected on the drift objection quoted in "Why".

Known cost, accepted: the bucket records the **allocation** date, while a feature is an *interval*. A feature opened 2026-08-28 and finished in October lives in `2026/08/`. The tree is therefore a birth index, not a work index, and must be described that way in `storage-rules.md` — never as "what we worked on in August".

### D3 — Leaf is the ticket ONLY, no slug — RATIFIED IN CONVERSATION 2026-08-26

`specs/2026/08/PROJ-123/`, not `specs/2026/08/PROJ-123-user-auth/`.

Known cost, accepted and stated once here: **`ls specs/2026/08/` becomes opaque** (`PROJ-123 PROJ-140 PROJ-155`), and the query "where is the auth thing, I don't remember the number" loses its directory-name answer and falls back to `grep -rl` over contents. The counter-argument for the bare ticket is real and is why it won: the title lives in the tracker, and a duplicated title in a directory name goes stale when the ticket is renamed.

### D4 — Ticket mandatory, via `REQUIRE_TICKET` in `.devforge/project-config.json` — **PARTIALLY ARGUED** — RATIFIED BY DIRECTIVE 2026-08-28, DELIBERATION PERFORMED 2026-08-29 AND THE DECISION UPHELD

"No ticket, no spec" as a **mechanical** trigger — no severity threshold, no judgment call, matching the zero-escape-hatch policy. But it is a **per-install policy key**, not a framework invariant, for two reasons:

1. **It is discipline, not verification.** The framework has no tracker integration and cannot confirm a ticket exists. `PROJ-0000` satisfies the rule with fake traceability. The emitted docs must say this plainly; a future session must not read the gate as a guarantee.
2. **It locks out installs with no tracker — including this repository**, whose own plans are `NN-TOPIC-PLAN.md` at the repo root.

`WORKSPACE_MODE` and `COMMIT_ATTRIBUTION` already live in `project-config.json`; this key joins them. At runtime the rule is binary — the escape hatch is closed at run time and the policy is chosen once, at configure time.

⚠ **This is the one place the plan deliberately breaks plan 75's tripwire** ("no new check number AND no new unnumbered hard-fail validator"). `REQUIRE_TICKET=true` *is* a new unnumbered hard-fail validator at intake. Declared here rather than smuggled: it is the mechanism the maintainer asked for, it is opt-in per install, and it adds no `verify-*` gate number to any PHASE-3.5 sequence. Everything else in this plan holds the tripwire.

⚠ **That break was ratified by directive on 2026-08-28 with the deliberation this ⚠ asks for NOT performed. It was performed on 2026-08-29 and D4 STANDS — narrowly, with its bounds stated.** The 2026-08-28 directive covered every item at once, and a blanket directive does not supply an argument that was never put; the argument is therefore recorded here in full. The case against comes first, because it is real and burying it would repeat the omission this ⚠ exists to flag.

**The case against the break.**

1. **Gates accumulate silently, and this one fires first.** That is why plan 75's tripwire exists: each added gate is unfalsifiable friction that nobody later removes. A hard fail at intake blocks the user's very first action in the pipeline — there is no earlier place to be stopped.
2. **The strongest objection: it buys discipline, not verification.** The framework has no tracker integration and cannot confirm a ticket exists, so `PROJ-0000` satisfies the rule. That is a new hard failure mode purchased without a corresponding guarantee — cost without proof, which is the worst shape a gate can have.
3. **Two behaviours to maintain and test forever, per install.** Both `REQUIRE_TICKET` states stay live paths indefinitely, and Phase 2's **Verify** already owes a test for each.
4. **The zero-escape-hatch policy cuts both ways.** Once `REQUIRE_TICKET=true` there is no override for a legitimate emergency — a hotfix with no ticket yet requires editing the config to proceed. That is the intended rigidity AND its cost; both halves are true.

**Why it stands anyway.**

1. **Opt-in, default `false` (OQ-1).** No install receives friction it did not choose. The tripwire's purpose is preventing *imposed* accumulation, and a key nobody must enable imposes nothing.
2. **Intake is the cheapest possible failure point.** It fires before any work exists. Contrast a finalize-side gate, which fails after everything is built.
3. **No PHASE-3.5 gate number is added.** The `verify-*` sequence is untouched, so the tripwire's first half holds completely; only the second half is broken, and only for installs that opted in.

**Two obligations this deliberation creates, and Phase 2 must satisfy both.** They are carried as Phase 2 tasks 5 and 6 so they are built rather than remembered:

- **The emitted text must say, in the consumer's own words, that the rule is discipline and not verification.** Stating it in this plan does not discharge it: a future operator reads the emitted docs, not this file, and must not read the gate as proof that a ticket exists.
- **The blocked message must name both routes out** — supply a ticket, or turn the key off — never a bare refusal. A hard fail whose message does not say how to proceed converts rigidity into a dead end.

D4 is binding and its content is unchanged by this deliberation; what moved is that the argument now exists. The reversal window is a fact about build state and is untouched here — D4 stays **reversible until Phase 2 begins**, nothing in Phase 1 depending on it. See `## Phase 0 close record`, which records both the omission and this closure.

### D5 — Branch name is `spec/TICKET` — RATIFIED IN CONVERSATION 2026-08-26

`spec/PROJ-123`, not `spec/2026/08/PROJ-123` (slashes are legal in git refs but buy nothing here).

⚠ **There is no free consequence here. Standalone `[PROJ-123] - Description` is NOT built by this plan and stays a known gap.** An earlier draft of this decision claimed the branch rename would hand `/devforge:finalize` the bracket format in standalone mode for the first time. It does not: that format is gated on **mode**, never on whether a ticket is extractable. `_implement/_cmds_commit.py:612-614` sets `ticket_id = ""` on the standalone arm — the ticket is never extracted there at all — and `_compose_message` (defined at `:244`) emits `"[{ticket_id}] - {title}"` only `if is_wrapper`, at each of its three mode branches (`:274` final, `:279` fix, `:284` task). `src/commands/finalize/main.md:201-202` says the same independently: the bracket format is labelled *"Source repo (wrapper mode only)"*, and standalone has no source repo. Closing that gap would mean making the gate ticket-driven rather than mode-driven in **both** `_cmds_commit.py` and `finalize/main.md`'s message-composition instructions — recorded here as out of scope, not as planned work.

⚠ **The mode-driven split is a decision, and it was re-ratified one day after this plan was drafted.** Plan 88 settled its fork 2 as arm **(i)** on 2026-08-26 — wrapper keeps `[TICKET-ID] - <title>` — while giving the cold-fix lane a **third** standalone shape, `fix(<scope>): <title>` (`_cmds_commit.py:277`). A split deliberately re-affirmed that recently is a reason to leave the gap alone here rather than close it opportunistically inside a layout plan; this strengthens the choice already made above, and changes nothing about it.

⚠ **One adjacent fact, stated at its true width and no wider.** Plan 88 also accepted that `_extract_ticket_id` falls back to the **full branch name** when the branch carries no `[A-Z]+-[0-9]+` token (`_cmds_commit.py:240-241`), so a cold wrapper fix on `develop` composes `[develop] - <title>` — a string seen at plan 88's ratification and accepted there. D5's `spec/<TICKET>` naming would make that fallback yield a clean ticket **on branches this framework created, and only those**: today's `spec/NNN-slug` carries no uppercase token and falls back too, whereas `spec/PROJ-123` extracts cleanly. It does nothing for `develop`, or for any other hand-made branch — which is exactly where plan 88's accepted string comes from. A narrow improvement on one branch class, not a fix for that string.

### D6 — `NNN` is retired; both shapes coexist forever — **NOT ARGUED** — RATIFIED BY DIRECTIVE 2026-08-28, DELIBERATION PERFORMED 2026-08-29 AND THE DECISION UPHELD

`next_spec_number` becomes dead, `SPEC_NUMBER_DIR_RE` becomes a *legacy-read* pattern, and `_feature_sort_key`'s `^(\d+)` no longer matches anything newly written.

**No migration** (plan 68 D3 precedent). Existing installs keep `specs/NNN-slug/` forever. Resolution must therefore **read both shapes and write only the new one**. This is the single largest correctness risk in the plan and Phase 3's **Verify** line is built around it.

Note the ordering consequence: sorting by ticket number is only *approximately* chronological, and interleaves across tracker prefixes (`ENG-*` vs `PROJ-*`). Any code that today relies on `NNN` for ordering must be re-examined rather than mechanically ported.

⚠ **Ratified by directive on 2026-08-28 with no deliberation performed. It was performed on 2026-08-29 and D6 STANDS — but on a weaker footing than D4's, and that difference is the most important thing this record carries.** D6 never came up in the originating conversation and was not argued in the ratifying session either; the blanket directive was the whole of what carried it, over what this decision itself calls the single largest correctness risk in the plan. The case against comes first, because it survives the decision rather than being answered by it.

**The case against.**

1. **Two live shapes forever is a permanent tax, and it is worse than the precedent it leans on.** Plan 68 D3 let legacy intake directories stand because they were *inert* — nothing wrote to them again. Here both shapes stay **live in the same install**: existing features keep `specs/NNN-slug/` while new ones arrive as `specs/YYYY/MM/TICKET/`, indefinitely. Every resolver, every test and every later layout decision pays for both, with no end date and no event that retires either arm.
2. **Ordering degrades, and the degraded contract is documented in nine places.** `_feature_sort_key` (`_implement/_cmds_resolve.py:99-113`) returns `2**31` for any directory name without a leading digit, so every new-shape leaf ties at the bottom of `/devforge:implement`'s queue. The phrase "lowest-numbered feature" is stated as the resolution contract at **nine sites** across `src/`, and after Phase 3 it describes only half the population. The sites are named in Phase 3's own ⚠, and re-stating them is the obligation below.
3. **`NNN` was cheap and it worked.** Zero dependencies, no config key, no validator, no external system. D6 trades it for an identity the framework cannot verify — the same objection D4's deliberation records as *its* strongest, arriving here as a consequence rather than as a gate.
4. **It was never argued.** D4 was *partially* argued: the maintainer picked its shape and only the tripwire break went unput. D6 never came up at all, in either session.

**Why it stands anyway — and this footing is WEAKER than D4's.**

**D6 is not a free-standing decision; it is ENTAILED by D2 and D3.** Those two were argued at length and each records the alternative it rejected — D2 the week level and a single combined `specs/2026-08/` segment *"proposed and declined by the maintainer"*, D3 the slug-bearing leaf — and each was ratified twice, in conversation on 2026-08-26 and again by the 2026-08-28 close. Once the leaf is the ticket and nothing else (D3), inside a `YYYY/MM` tree (D2), `NNN` has nowhere left to live. **Reversing D6 alone is therefore incoherent: it would mean reopening the layout**, and the layout is the part that actually was argued.

Say that plainly rather than presenting the two as equally settled. D4 stands on its own merits — opt-in, default `false`, the cheapest possible failure point, no gate number added. D6 stands because its parent decisions stand. A session that reverses D2 or D3 gets D6 back for free; one that keeps the layout and revives `NNN` is asking for a leaf name D3 already rejected.

**Two further points belong in this record.**

- **Coexistence is forced, not preferred.** Nothing here argues that two live shapes are good. The only alternative is migrating existing installs, which plan 68 D3's precedent rejects and which nobody requested. "Both shapes forever" is the price of not migrating, paid knowingly.
- **The ordering loss has a defined shape, not an undefined one.** `iter_feature_dirs` (`_shared/feature_alloc.py:374`) already emits every legacy dir before every new-shape one — legacy by `NNN`, new-shape by `(YYYY, MM, leaf)` — and `_glob_feature_dirs` (`_implement/_cmds_resolve.py:116`) re-sorts that list with `_feature_sort_key` (`:132`), which is a **stable** sort tying every new-shape leaf at `2**31` (OQ-2's ratified `[A-Z]+-[0-9]+` ticket pattern starts with a letter, so no leaf carries a leading digit). The tie therefore preserves the accessor's order instead of scrambling it: a mixed install drains legacy features in `NNN` order first, then new-shape features in allocation-date order. That is coherent and defensible — it simply is not what the words "lowest-numbered feature" say.

**One obligation this deliberation creates, and Phase 3 must satisfy it.** It is carried as Phase 3 task 7 so it is built rather than remembered: **the "lowest-numbered feature" contract is re-stated at all nine sites**, describing what resolution actually does on a mixed install. Without it the phrase goes false at nine places the moment the layout ships, and nothing mechanical will say so. This is the prose half of the ordering note above — that note sends Phase 3 at *code* relying on `NNN` for ordering; task 7 covers the sentences that *describe* the ordering.

D6 is binding and its content is unchanged by this deliberation; what moved is that the argument now exists, and that its dependence on D2 and D3 is stated rather than assumed. The reversal window is a fact about build state and is untouched here — D6 stays **reversible until Phase 3 begins**. ⚠ **This closure is recorded HERE and not in `## Phase 0 close record`.** That section's third caveat bullet and the D6 clause of its closing ⚠ both still say the deliberation is not performed, and are stale on that point from 2026-08-29; they are left standing because that ⚠'s own closing sentence declares which edits are its only 2026-08-29 ones, so a third would falsify it. Read that section for the omission; read this for the closure.

### D7 — Provenance stamp: `Run by:`, on travelling artifacts only

Four artifacts: `spec.md`, `plan.md`, `summary.md`, `research-report.md` — the ones that get pasted into PRs, tickets and Obsidian, where git metadata does not follow.

**Not** task files: they never leave the repository, and stamping 40 of them per feature pays 40× for nothing.

**Named `Run by:`, not `Author:`.** The document is composed by the model and approved by the human; a field named `Author` on a document whose author wrote none of it misleads exactly where accountability matters. A future reader must be able to tell "who ran this" from "who decided this".

### D8 — `**Author**: Claude + User` (`_specify/_render.py:135`) is REPLACED, not supplemented

One provenance line per artifact. Two adjacent lines, one of which is a constant that names nobody, is worse than either alone.

### D9 — The stamp is config-gated and never invented

- Value source: `git config user.name`, captured at **creation** time.
- Unset / unavailable → the line is **absent**. Never `unknown`, never a placeholder. A fake value is worse than no value.
- **Config-gated.** An install that answered "no attribution in files" must not get a real human name stamped into them by another route (`_configure/_render.py:148-150`, the `ai_attribution == "Yes"` gate itself). *Which* gate carries that — the existing `ai_attribution` answer, or a new key of its own — is **OQ-8**; nothing in this plan presumes a new key exists.
- The emitted text must state the bound: the field records the **creator**, and later edits (grill re-entry rewriting `spec.md`, `**Status**:` flips) do **not** update it. Without that sentence the field becomes exactly the "used to be true, now silently false" failure mode `CLAUDE.md` names as most dangerous. **A per-edit trail is explicitly NOT built** — that is `git log --follow` reimplemented in markdown inside a git-tracked file.

---

## Open questions (OQ-1 – OQ-8)

- **OQ-1 — `REQUIRE_TICKET` default.** `false` (opt-in) or `true` (opt-out)? Note this repository needs `false`. Recommendation: default `false`, and let `/devforge:configure` ask, defaulting to `true` when `WORKSPACE_MODE` is wrapper (wrapper mode implies an external tracker by construction).
- **OQ-2 — Ticket format and letter case.** Constrain to `[A-Z]+-[0-9]+` (matching `_TICKET_PATTERN`, so the framework has one ticket notion rather than two), or accept free-form? And: an uppercase directory name is new — `FEATURE_NAME_RE`'s lowercase-only convention dies with the slug. ⚠ On a case-insensitive filesystem (macOS default) `PROJ-123` and `proj-123` collide while on Linux they do not; whichever is chosen must be **normalized at allocation**, not left to the typist.
- **OQ-3 — Bucket source.** `YYYY/MM` from the allocation date — confirm, and confirm the timezone/clock source (local date, as `set-date` already enforces `YYYY-MM-DD` elsewhere).
- **OQ-4 — Does `REQUIRE_TICKET` reach `bugs/NNN-*.md`?** Plan 88 is **CLOSED 2026-08-27 (build)** — Phases 0–4 complete 2026-08-26, Phase 5 consumer e2e deferred and not run. This is fact, not forecast: `bugs/NNN-*.md` is now the **third** `/devforge:fix` findings source, consumed by a feature-less cold mode, and a `fix_helper close-bug` verb writes three fields back into the one consumed bug file. Recommendation: **no** — bug files are not features, keep them `bugs/NNN-slug.md`, and record that as a stated boundary so plan 88 is not silently constrained by this one. ⚠ The recommendation is not merely undisturbed by plan 88 shipping; it is **corroborated** by it. Plan 88 built that lane feature-less **by decision** (D2 bypasses `/devforge:fix` PHASE 0.2 / 0.3 / 0.4 precisely because no `--feature` exists), so a ticket rule scoped to intake-allocated feature directories and a lane deliberately built without one agree by construction rather than by luck. The two original reasons stand unchanged: plan 88 introduced no naming change, and its cold lane resolves a bug file by the path the user types (`/devforge:fix bugs/NNN-<slug>.md`), so a rename would break a user-facing argument form.
- **OQ-5 — Attach mode.** A `/devforge:grill` re-entry reuses an existing directory and skips allocation (plan 68 D6). Confirm the ticket rule is a **no-op** there, and that the ticket is recovered from the path rather than re-asked. ⚠ Plan 85 has since made `/devforge:grill` **mandatory to run** — `/devforge:breakdown` blocks until a grill report exists for the resolved plan — so a grill run is no longer opt-in and attach-mode re-entry becomes *more* likely, not less. That raises the value of getting this answer right; it does not change what the answer should be. The `_grill/_scope.py` citations in "Verified ground truth" were re-verified 2026-08-27 and did not move.
- **OQ-6 — Legacy read surface.** Which of the six depth-1 resolvers must read the legacy `specs/NNN-slug/` shape, and which may drop it? Recommendation: **all six read both** — a resolver that silently stops seeing an old feature is a data-loss-shaped bug, not a cleanup.
- **OQ-7 — Re-render behaviour.** When `/devforge:specify` rewrites `spec.md` on a grill re-entry, does `Run by:` keep the original value or take the current one? D9 says creator, so: **keep the original** — which means the re-render must *read back* the existing value rather than recompute it. Confirm this is worth the complexity, or accept "the last full render wins" with the bound stated. Whichever way this lands decides whether Phase 4's task 6 is in scope — `render_spec` (`_specify/_render.py:118`) is a pure function of `state` with no file read-back today, so "keep the original" is a real code change and not a free property.
- **OQ-8 — Which config key gates the `Run by:` stamp?** D9 requires a gate and names none; no such key exists today. **(i) No new key — the stamp rides the existing `ai_attribution` answer directly (RECOMMENDED)**: one fewer key, and the two semantics are close enough that a second toggle mostly invites a pair of settings that contradict each other. **(ii) A new named key**, defaulting from the `ai_attribution` answer — which additionally pays the full multi-file config-key cost Phase 2's ⚠ describes (`E2E_COMMAND` reached four Python modules plus `/devforge:configure` prose, with a fail-closed required-field loop among them), for a toggle whose value an existing answer already carries. That is a further argument for (i); the recommendation above is unchanged. Whichever is ratified must reach Phase 4 with the same specificity `REQUIRE_TICKET` gets in Phase 2 — a named read site, a `/devforge:configure` question (or an explicit statement that there is none), and a render path.

---

## Phase 0 close record

**Closed 2026-08-28 by maintainer directive.** The ratifying act was a single one-word directive — *"implement"*, given in Ukrainian — at the end of a session in which this file's D-item and OQ-item recommendations were presented and argued. **Every item ratifies AS RECOMMENDED: D1–D9 and OQ-1–OQ-8.** No recommendation is amended by this record and no decision body above is rewritten; the `### D…` heading markers and this section are the current state.

**D1 = (a).** F1 first: the helper becomes the sole author of the path and the 388 hand-composed occurrences are retired *before* the layout changes. The consequence is that **Phases 1, 2 and 3 stand exactly as written** — D1's ⚠ about arm (b) requiring a restructure of Phases 1–3 is discharged, and is marked `DISCHARGED 2026-08-28` where it sits rather than deleted.

**This ratification is weaker than an item-by-item one in three specific ways.** They are recorded rather than smoothed, because a future session reading "every item as recommended" would otherwise assume a deliberation that did not happen:

- **D1 was never answered in its own words.** It was put to the maintainer three times across the session and never picked; the blanket directive is what carries it. Read the consequence narrowly: **Phase 1 is the only phase this actually unblocks.** Phases 2 and 3 can still be re-cut if the maintainer reverses D1 before Phase 1 lands.
- **D4's tripwire break was ratified by omission — which this file's own text says must not happen.** The "That leaves D4 and D6" paragraph states D4 *"requires full Phase-0 deliberation"* precisely because the break of plan 75's tripwire was never put to the maintainer as a decision, and a blanket directive does not supply that deliberation. D4 is therefore **ratified by directive with the deliberation NOT performed** — not "ratified", and it must not be restated that way. Nothing in Phase 1 depends on it, so it stays **reversible until Phase 2 begins**. **DELIBERATION PERFORMED 2026-08-29 — D4 UPHELD.** The argument this bullet records as missing was made on 2026-08-29 and the decision stands, narrowly, with its bounds stated: the case against (four points, the strongest being that the rule buys discipline and not verification), the three reasons it stands anyway, and two obligations now carried as Phase 2 tasks 5 and 6. It is written out in full in D4's own ⚠ rather than here. **The bullet above is not rewritten** — the omission it names did happen, and this line records the closure, not a different history. D6 is untouched by it.
- **D6 was likewise never argued.** Retiring `NNN` as the feature identity never came up in the originating conversation and was not argued in the ratifying session either. Same treatment: **ratified by directive, deliberation NOT performed**, and **reversible until Phase 3 begins**.

**Four ratified items whose forks carry real downstream consequences.** Each is ratified as recommended, and each recommendation gets exercised in the phase named. A future session should re-read the item itself before building that phase rather than working from this summary:

- **OQ-1 — `REQUIRE_TICKET` default.** Ratified as recommended: default `false`, `/devforge:configure` asks, and the question defaults to `true` when `WORKSPACE_MODE` is wrapper. Exercised at **Phase 2**, task 3.
- **OQ-2 — ticket format and letter case.** Ratified as recommended. The item labels no arm `Recommendation:` but argues one — `[A-Z]+-[0-9]+`, matching `_TICKET_PATTERN` so the framework carries one ticket notion rather than two — and its ⚠ is not optional: the macOS case-insensitivity trap is closed by **normalizing at allocation**, never by leaving case to the typist. Exercised at **Phase 2**, task 2, which is where the exact pattern and the normalization rule get written.
- **OQ-7 — re-render read-back.** Ratified as recommended: **keep the original**. That **puts Phase 4's task 6 in scope** — `render_spec` (`_specify/_render.py:118`) is a pure function of `state` today and gains a read-back it does not have. Exercised at **Phase 4**.
- **OQ-8 — which config key gates the `Run by:` stamp.** Ratified as recommended, option **(i)**: the stamp rides the existing `ai_attribution` answer and **no new config key is added**. Exercised at **Phase 4**, task 4.

**Reading the pre-close text.** Nothing above `## Decisions to ratify (D1–D9)` was rewritten to past tense, and neither was that section's own preamble. It still says *"**D1 is genuinely unanswered** and must be settled first"*, still says D4 and D6 *"must not be waved through by omission"*, and still says each *"requires full Phase-0 deliberation"*. Those sentences record the plan's state BEFORE 2026-08-28 and are preserved deliberately — the last two are the very text the D4 and D6 caveats above lean on, so removing them would erase the record of what was skipped.

**Nothing is built.** Phase 0 is the only closed phase; Phases 1–6 have not started. The close produced changes to this file only — this section, the ratification markers in the `### D…` headings, and Phase 0's own CLOSED marker. The `CLAUDE.md` active-plan index line and the `PLAN-STATUS-ARCHIVE.md` entry are still owed by Phase 5 and do not exist yet. The **Status** field at the top of this file remains the authority.

⚠ **Superseded the same day, and preserved unedited rather than rewritten.** The paragraph immediately above records the state **at close** on 2026-08-28. **Phase 1 was built later that same day** — see Phase 1's build record — so *"Nothing is built"* and *"Phases 1–6 have not started"* were true when written and are false now. No decision, disposition or caveat in this section is withdrawn, and nothing above this marker is edited; only the build state moved. Two consequences follow mechanically from this section's own text and are stated so they are not missed:

- **D1's reversal window is CLOSED.** The first caveat above says Phases 2 and 3 *"can still be re-cut if the maintainer reverses D1 before Phase 1 lands."* Phase 1 has landed, so that condition is spent — reversing D1 now would mean unwinding shipped work, not re-cutting unstarted phases.
- **D4 and D6 remain reversible on their stated terms.** D4 is reversible until Phase 2 begins and D6 until Phase 3 begins; neither phase has started, and Phase 1 depended on neither. Their deliberation is still NOT performed and this marker does not supply it. **AMENDED 2026-08-29 — that last sentence is now true of D6 ONLY, and is amended rather than rewritten**: D4's deliberation was performed on 2026-08-29 and its decision upheld (see D4's ⚠ and the D4 bullet above). **D6's is still NOT performed.** Neither reversal window moved — Phase 2 and Phase 3 have both still not started. This bullet's amendment and the D4 bullet's own are the only 2026-08-29 edits in this section, so the marker's *"nothing above this marker is edited"* describes the 2026-08-28 act that wrote it and is not a standing invariant over the region.

The `CLAUDE.md` index line and the `PLAN-STATUS-ARCHIVE.md` entry are **still owed by Phase 5 and still do not exist** — Phase 1 shipping did not change that, and neither was written for it.

---

## Phases

Each phase must leave the tree buildable and the suite green.

### Phase 0 — Ratification — **CLOSED 2026-08-28**

Settle D1–D9 and OQ-1–OQ-8. Re-verify the two facts this plan leans on hardest before any code moves: the 388 prose-occurrence count (re-derive it with `grep -rho 'specs/' src/commands --include="*.md" | wc -l`, the same method that produced the figure — and expect a different number again, since it moved 386 → 388 between 2026-08-26 and 2026-08-27), and the absence of a `feature_dir`/`path` key in the handoff schemas.

**Closed 2026-08-28**, dispositions in `## Phase 0 close record` above and in the `### D…` headings themselves. Both demanded re-verifications are **done**: the occurrence count was re-derived on **2026-08-27** with the command named above and is **388** — the figure this file carried throughout at the moment of close, and **superseded by Phase 1's sweep the next day (69 across 17 files), then by Phase 1b's on 2026-08-29 (45 across 14); the 388 here is the pre-build baseline and the 69 an intermediate reading — neither is current** — and the research / specify / discover handoff schemas were confirmed to carry **no** `feature_dir` key and **no** `path` key, so Phase 3 may rely on that.

**Verify**: every D and OQ has a recorded answer in this file; no phase below has started.

### Phase 1 — Opaque `feature_dir` (gated on D1 = (a)) — **BUILT 2026-08-28**

The helper becomes the sole author of the layout. Command prose stops containing the literal `specs/`.

**Scope.** This phase covers the **intake-allocated feature path only**. Plan 88's cold `/devforge:fix` lane holds no feature directory by design, so the accessor below must not be specified as though every caller has one — see the feature-less-path bullet under "Adjacent facts that constrain this plan".

1. A single resolution accessor, in `_shared/feature_alloc.py` alongside `allocate_feature_dir`, that returns a feature directory path given a feature reference — covering both the allocate path and the resolve path (the six depth-1 consumers).
2. `allocate-feature-dir`'s stdout keeps `path` as the value callers use; `dirname` / `number` / `formatted_number` become **legacy-only** keys (still emitted for the un-migrated shape, not consumed by new prose).
3. Sweep the 388 prose occurrences in the 26 command-spec files onto `<feature_dir>` — the value the helper handed the orchestrator — so that no command spec knows what is inside the path.

⚠ **Build the accessor for a variable-depth tree from the start.** The legacy shape `specs/NNN-slug/` is **one** level below `specs/`; the shape D2 introduces, `specs/YYYY/MM/TICKET/`, is **three**. All six of today's consumers do a single flat scan of `specs/`, and under the new layout a flat scan enumerates *year* directories — it cannot see a new-shape feature directory at all. Reading both shapes is therefore a genuine algorithmic branch dispatched on shape, not a regex swap. An accessor written here as a straightforward flat `iterdir()` will satisfy Phase 1's own Verify (only the legacy shape exists yet) and then need rewriting at Phase 3; put the depth branch in now, with the legacy arm as the only one that currently returns anything.

**BUILT 2026-08-28 on `develop-2.0-init`**, in four groups, in this order:

- `e8848be` — **the accessor (item 1)**. `specs_root_for(devforge_dir)` (`_shared/feature_alloc.py:346`), `iter_feature_dirs(specs_root)` (`:374`) and `find_feature_dirs_with(specs_root, filename)` (`:514`), carrying the two-arm variable-depth walk the ⚠ above demanded — the legacy arm is the only one that returns anything today. All six depth-1 resolvers migrated onto it in the same commit, so the depth assumption now lives in one function instead of six.
- `535b01f` — **the diagnostic that migration cost**, recorded at the call site rather than repaired. See the **Verify** amendment below; this is the one place Phase 1 changed observable behaviour.
- `0fc1d62` — **`allocate_feature_dir` gained a `relative_path` key** (`:332`). ⚠ **Item 2 above shipped in a REFINED shape and must not be read as written.** Item 2 says `path` stays *"the value callers use"*; the build instead made **`relative_path` CANONICAL for path ARGUMENTS and for anything written into an artifact**, and demoted `path` to user-facing messages only — because `path` is absolute and leaks the local filesystem layout into committed text (`:244-254` / `:255-273`). `number`, `formatted_number` and `dirname` did become legacy-only exactly as item 2 said, each marked `LEGACY-SHAPE-ONLY` in the docstring with the bound stated (`:274-292`).
- `af92a1f`, `3f7d5a4`, `75704c6`, `718f2fd`, `cf1df21`, `5d6e41e`, `f99b114`, `b904db1`, `bd9e69d`, `4cddea2`, `92c0a7c`, `452d587`, `dcf2b42`, `6963bbf`, `22162eb` — **the prose sweep (item 3)**, 26 files.

**Result: 388 `specs/` occurrences → 69, across 17 files (was 26).** Every survivor falls in one of the four classes the amended **Verify** names.

**The defect harvest — nine pre-existing defects the sweep surfaced, recorded with their fate.** They are recorded because three of them share one cause and that cause is an argument about spelling, not a tally of bugs found:

- **Three double-prefix bugs, one cause.** `/devforge:review`, `/devforge:spec-check` and `/devforge:summarize` each emitted `specs/specs/<dir>/file`, because a file-local token named `<feature>` was *defined* as the full path **including** the `specs/` root and authors kept prepending the root anyway. All three repaired by the sweep. **This is the strongest argument for the `<feature_dir>` spelling item 3 adopted**: a token whose name says *directory* does not invite a prefix, whereas one named `<feature>` reads like a bare slug and invites one. The lesson is about the name, not about the three sites.
- `src/commands/grill/references/report-format.md` asserted a `specs/` prefix on the report's `**Feature**:` line that `_grill/_report.py:561` never emits — repaired.
- `src/commands/fix/main.md`'s Stage-B question named a value that does not exist on any cold run (a gap left by plan 88's cold-fix lane) — repaired.
- `/devforge:constitute` described a glob that plan 53 Phase 7a deleted, at three prose sites plus a Python comment, and used it as **load-bearing justification** rather than as background; the same rule's behaviours still listed the retired Check 5. All repaired in `22162eb`.
- ⚠ **Two reported and deliberately NOT repaired — each needs a decision this sweep had no standing to make, and neither is closed:**
  - `src/commands/grill/references/report-format.md:73` writes the skeleton with an em-dash where the renderer emits ASCII `--` (`_grill/_report.py:563`). It is unknown which side is right, so neither was changed.
  - `src/commands/implement/references/crash-recovery.md:7` says the WIP-marker fields are *"written by the `_implement/_wip.py` helper module"*, but `write_wip_marker` (`_implement/_wip.py:88`) has **no production caller** — only `tests/lib/_implement/test_wip.py` — and the live writer is the orchestrator. Either the prose is wrong or the helper is unreachable; that is not a spelling question.

  ⚠ **AMENDED 2026-08-29 — BOTH reports are now CLOSED, in `324942c`. The two bullets above are kept as the historical record of what the sweep found and why it declined to act; they are no longer a live to-do list, and the first of them now quotes a string that is GONE from the tree.**

  - **The em-dash report — closed by ruling for the renderer.** `report-format.md` now states the rule outright before the skeleton (`:69-71`): the `--` separators are ASCII *"because `_report.py` emits them that way"*, and the em-dashes still in the document mark its own annotations, which the renderer never emits. The skeleton line itself is ASCII (`:74`). `_grill/_report.py` was not changed.
  - **The `crash-recovery.md` report — closed by ruling the PROSE wrong.** `:7` now reads *"PHASE 2 writes the file directly and PHASE 0 parses it back; `_implement/_wip.py` states the same field shape in code, and both ends must honour it."* ⚠ **The bullet above quotes *"written by the `_implement/_wip.py` helper module"* verbatim and that string NO LONGER EXISTS in the tree** — do not grep for it expecting a hit. ⚠ **What the fix did NOT do: `write_wip_marker` is STILL production-unreachable** (grep-verified 2026-08-29 — `tests/lib/_implement/test_wip.py` remains its only caller). The report was closed by correcting the claim about who writes the file, not by wiring the helper up. That unreachability is a live fact this plan neither owns nor fixes.

**Verify** — **AMENDED 2026-08-28; the original could not pass and is quoted here rather than deleted**: the original read *"returns only (a) `storage-rules`-style descriptions of the layout, and (b) nothing that instructs the model to compose a path."* **Clause (b) is unmet by design.** The sweep found a class the plan did not anticipate — globs the **orchestrator runs itself** (`specs/*/grill-seed.json`, `specs/*/*-seed.json`, `specs/*/review.md`, and `specs/NNN-*` directory enumerations). Closing them requires helper verbs over `find_feature_dirs_with`, i.e. Python this phase was not scoped to write; they are deferred to Phase 1b. The amended bar is **not** that survivors are few — it is that **every** survivor falls in a named class. `grep -rn 'specs/' src/commands --include="*.md"` returns 69 occurrences across 17 files, and each is exactly one of:

- **(a)** a bare `specs/` naming no child — the artifact root as a location, with nothing composed under it.
- **(b)** the **discovery-glob class**, deferred to Phase 1b and inventoried there. **CLOSED at Phase 1b on 2026-08-29** — migrated onto `artifact_helper find-feature-artifacts` across eleven command specs; **exactly one deliberate site survives**, and Phase 1b's **Verify** names it and gives the reason it stays.
- **(c)** a transcription of a literal the helper composes — quoted so the reader sees what the helper produces, never an instruction to build it.
- **(d)** `specs/` meaning the **artifact root** rather than a feature directory (e.g. the linter-ignore folder list, the wrapper-mode artifact-location rule).

Full suite green. ⚠ **The original's closing sentence — *"No behaviour change is visible to a consumer"* — is FALSE in exactly one narrow, recorded way and is amended, not retained**: `/devforge:grill`'s `resolve_target_feature` can no longer distinguish an **unreadable** `specs/` from an **empty** one, because `iter_feature_dirs` treats any `OSError` while probing `specs_root` as `[]` and the caller's own `os.listdir` branch — which returned a distinct `"cannot list {0!r}: {1}"` error — was deleted at the migration. A **missing** `specs_root` is unaffected and still reports distinctly, via the `os.path.isdir` check that runs before the accessor. This was accepted rather than repaired (duplicating a diagnostic on top of the accessor's OSError-means-absent contract fights that contract) and is recorded in `_grill/_scope.py`'s own docstring by `535b01f`. Every other consumer-visible behaviour is unchanged — the same directories are created at the same locations.

⚠ **AMENDED 2026-08-29 — that last sentence is FALSE a SECOND time, and this second break is a REGRESSION, not an accepted trade-off.** *"Every other consumer-visible behaviour is unchanged"* did not hold: the Phase-1 prose sweep silently broke source-origin tagging at `/devforge:specify`, and Phase 1b fixed it at the cause in `9bf49aa`. The full account — what broke, why three green suites missed it, and why the classifier rather than the prose was the thing repaired — is in **Phase 1b's build record**: recorded THERE because the fix is a Phase-1b commit, and pointed at from HERE because the defect is Phase 1's. **Phase 1's claim was made in good faith and its Verify was met as understood at the time** — the four survivor classes were correctly enumerated and the suite genuinely was green. What that Verify could not see is that the green suite covered nothing capable of noticing. Nothing above this marker is withdrawn or rewritten.

### Phase 1b — The discovery-glob class — **BUILT 2026-08-29**

**Why it exists.** A `specs/*/x.json` or `specs/NNN-*` glob hardcodes depth 1. At Phase 3 it stops matching **entirely** — the same latent break `_grill/_scope.py` carried until `e8848be` fixed it, except here it lives in prose, where no test catches it. That is the whole case for the phase: Phase 1 removed the depth assumption from the six Python resolvers and left an identical assumption standing in the orchestrator instructions beside them.

**The inventory**, taken from the sweep's own reports on 2026-08-28 so this phase starts from a list rather than a re-scan. ⚠ These are line numbers, and line numbers move — re-grep before editing, and use the list to know *what to look for*, not to navigate blind:

- `src/commands/research/main.md:141`, `:155` — `specs/*/grill-seed.json`
- `src/commands/discover/main.md:153`, `:167` — `specs/*/grill-seed.json`
- `src/commands/plan/main.md:104`, `:117` — `specs/*/*-seed.json` (project-wide by decision — plan 83 recorded the divergence from `/devforge:specify`'s dir-scoped glob; Phase 1b changes the depth, not that scoping)
- `src/commands/specify/main.md:139` ×2, `:156`, `:242` ×2 — `specs/<resolved-feature-dir>/*-seed.json` plus the `specs/*/` shape it forbids, and §1.7's `ls specs/` prior-spec enumeration
- `src/commands/review/main.md:83`, `:85` — `specs/NNN-*` directory enumeration
- `src/commands/fix/main.md:121`, `:123` — `specs/NNN-*` directory enumeration
- `src/commands/verify/main.md:76`, `:78` — `specs/NNN-*` directory enumeration
- `src/commands/finalize/main.md:61`, `:63` — `specs/NNN-*` directory enumeration
- `src/commands/summarize/main.md:56`, `:58` — `specs/NNN-*` directory enumeration
- `src/commands/audit/main.md:35`, `:440` — `specs/*/review.md`
- `src/commands/spec-check/main.md:75` — `specs/NNN-*` directory enumeration; `:78` — `ls -t specs/[0-9]*/spec.md`, ⚠ **the only site in the class that is a literal shell command rather than an instruction**, so it breaks at Phase 3 without any model in the loop to notice. **Found 2026-08-28 while writing this phase, NOT in the sweep's own report list** — treat the rest of the inventory as verified-but-not-proven-complete for the same reason.

⚠ **One borderline this phase must classify rather than assume.** `src/commands/specify/main.md:493` spells `specs/*/discovery-report.md` inside a context-source list — it names a pattern but instructs no glob, so it may belong to Phase 1's class (c) instead. Decide it explicitly; do not let it fall between the two phases.

**DECIDED 2026-08-29 — class (c), and left as written.** The site is now `src/commands/specify/main.md:501` (line numbers moved, as that ⚠ warned). It transcribes a literal that lives in **helper code** — `_specify/_schema.py:293`'s `greenfield_feature` base-reads tuple carries the string `specs/*/discovery-report.md` verbatim — so the prose is quoting what the helper already holds, names a pattern, instructs no glob, and no model acts on it. It did not fall between the phases.

**The shape of the fix.** A discovery verb in **each consuming command's own helper**, delegating to `_shared/feature_alloc.py`'s `find_feature_dirs_with`. ⚠ **The constraint that makes "the consumer's own helper" the safe home, and not merely a stylistic pick:** every seed-reading block deliberately forbids calling the **producing** command's helper — `/devforge:research` Phase 0.6, `/devforge:plan` PHASE 0a.7 and `/devforge:specify` Phase 0.5 each say to parse the matched JSON inline so the block *"stays valid even if"* the producing command is ever removed. A verb in the consumer's own helper preserves that property; a shared verb on the producer's helper would destroy the exact resilience those blocks were written for. `specify_helper find-handoffs` (`_specify/_cmds_handoff.py:1014`) is the existing precedent for a discovery verb living on the consumer side.

**Sequencing: before Phase 2.** Not because Phase 2 depends on it, but because Phase 3 breaks this class **silently** — a glob that stops matching produces an empty result, not an error — and Phase 2 sits between the two. Leaving 1b until after Phase 2 narrows the window in which the break can be caught by reading rather than by a consumer hitting it.

Plan 75's tripwire holds, both halves: these are discovery **verbs**, not gates — no new `verify-*` gate number, no new check number, no new unnumbered hard-fail validator.

**BUILT 2026-08-29 on `develop-2.0-init`**, in seven commits, in this order:

- `617a867` — **the shared discovery verb.** `artifact_helper find-feature-artifacts` (`_artifact/_cmds_find_artifacts.py`), delegating all directory-layout scanning to Phase 1's `iter_feature_dirs` / `find_feature_dirs_with` and adding only per-directory filename filtering of its own.
- `049022e` — **`mtime_ts` / `mtime_iso` on every match, plus `matches_by_recency`.** Added after checking the verb against the real 26-site inventory: **seven of the eleven files needed recency and the verb as first built could not serve them.**
- `05aa894` — **`--limit N`, plus the two convention exemplars** (`/devforge:research` as class A, `/devforge:review` as class B). The flag exists so class B reads stdout directly instead of extracting through `python3`, which would have added that dependency to `/devforge:summarize` and `/devforge:finalize`, neither of which has it today.
- `b4b93bf` — **`/devforge:fix` and `/devforge:spec-check`**, the two sites the convention exemplars marked uncovered.
- `329a31e` — **`/devforge:discover`, `/devforge:plan`, `/devforge:verify`, `/devforge:finalize`, `/devforge:summarize`.**
- `a6bde45` — **`/devforge:audit` and `/devforge:specify`**, plus a repair to `/devforge:verify`'s helper-interaction sentence.
- `9bf49aa` — **the regression fix.** Not a migration commit at all; see "The regression Phase 1 introduced" below.

⚠ **"The shape of the fix" above shipped in a REFINED shape and must not be read as written.** It scoped *"a discovery verb in **each consuming command's own helper**"*. The build instead put **ONE shared verb on `artifact_helper`**. The decoupling constraint that paragraph names is what makes that safe rather than merely cheaper: `artifact_helper` is **nobody's producing helper** — it is shared infrastructure the consuming commands already call for `commit-artifacts` — so a verb here preserves exactly the property the seed-reading blocks were written for, which a verb on a *producing* helper would have destroyed. `specify_helper find-handoffs` remains the consumer-side precedent that paragraph cites; it is not contradicted, only not copied eleven times.

**Result: 69 `specs/` occurrences → 45, across 14 files (was 17).** Re-derived 2026-08-29 with the same method every earlier reading used — `grep -rho 'specs/' src/commands --include="*.md" | wc -l`. All eleven inventoried files are migrated. Three of the literals this class was spelled with are confirmed gone: `specs/*/grill-seed.json` and `specs/*/*-seed.json` are absent from `src/commands`, and `ls -t specs/[0-9]*/spec.md` — the class's only literal shell command — is absent from all of `src/`. ⚠ **Those three greps are spot-checks, not a proof the class is empty** — the **Verify** below states why no single pattern can be one, and that reasoning is unchanged by the class having been closed.

⚠ **Two different eleven-member sets exist here; do not conflate them.** The **eleven files that now call `find-feature-artifacts`** are `audit`, `discover`, `finalize`, `fix`, `plan`, `research`, `review`, `spec-check`, `specify`, `summarize`, `verify` (grep-verified 2026-08-29). `breakdown` and `grill` are **not** among them — they call `artifact_helper` for `commit-artifacts` only, which is why `artifact_helper` has **thirteen** command-spec callers in total while this verb has eleven.

**What building this phase discovered.** Recorded because each one changed how the work was sequenced, not merely what it produced:

- **The verb was rebuilt twice before any prose migrated, both times from checking it against the consumer inventory rather than against a spec.** The first pass served **4 of the 26 sites**; the mtime pass served the seven-file recency class it could not reach; `--limit` removed a `python3` dependency the workaround would otherwise have imposed on two commands. **That is the argument for checking the inventory BEFORE the migration rather than after** — every one of those gaps was found by reading real consumers, and none of them was visible from the verb's own contract. Had the prose gone first, each would have surfaced only once eleven files had already been rewritten against a verb that could not serve them.
- **A conflation hazard the migration created and then caught.** `find-feature-artifacts`'s match record has a `file` key meaning **the review's own path**, while `map-recurring-issues` takes a `[{file, fingerprint}]` list whose `file` means **the SOURCE file a past finding named** (`_audit/_rank.py:70-160`; the substring match is at `:90-94`). Writing review paths into that key would have made every past entry match nothing and read as RESOLVED. Disambiguated at the site (`src/commands/audit/main.md:450`), which now states outright that a match record's `file` must not be carried into that key.
- **A fourth double-prefix instance, in `/devforge:specify`** — the same bug class Phase 1's harvest found three of, and the reason that harvest called the lesson *"about the name, not about the three sites"*. Here an undefined second token `<resolved-feature-dir>` was prefixed with `specs/`, while the file already defines the resolved directory as `<feature_dir>` — **the whole path**. Since `find-handoffs` prints an absolute path, the composed glob was **unreachable, not merely ambiguous**: no file could ever match it.

**The regression Phase 1 introduced.** Fixed in `9bf49aa`. Recorded as a regression, not as a discovery:

Phase 1 replaced a composed `specs/<NNN>-<slug>/…` path in `specify/main.md` with `<feature_dir>/…`. At that command the token is **absolute** — `find-handoffs` emits a resolved `handoff_path`, and `main.md:15` binds `<feature_dir>` to that path's parent — so `record-input-read` began receiving absolute paths. `source_origin_for_path` classifies on `p.startswith("specs/")`, so those reads started tagging **`context`** instead of `research` / `discover`. That falsified the three sentences at `specify/main.md:170`, `:226` and `:262` which state that the tag is decided by filename under `specs/`, and it meant **Phase 3's discover pre-seed, keyed on `source_origin == "discover"`, could never fire**.

Three points this record must carry:

- **No test caught it.** Three full green suites ran across Phase 1 and not one failed, because **no test covered this classification at all**. A green suite proves only that what is covered did not break — it is not evidence that nothing broke.
- **It was fixed at the cause.** Putting the composed path back would have hidden the defect and undone the very thing Phase 1 exists to remove. The classifier was wrong **on its own terms** — the same file must classify identically however its path is spelled — and the bug **predates the sweep**, which merely started exercising it. `source_origin_for_path` gained an optional `root` (`_specify/_topic.py:83`); absent `root` it reproduces the prior behaviour exactly, so no existing caller changed.
- **It had a second instance.** `_group_for_path` (`_specify/_cmds_phase01.py:348`) duplicated the same normalization independently and mis-bucketed the rendered findings. The two functions were **deliberately NOT merged**: they answer different questions, and `context` is a one-to-many fan-out onto four separate render headings. Only the duplicated normalization moved to a shared helper (`normalize_source_path`, `_topic.py:142`).

**Two findings this phase surfaced and deliberately did NOT fix — neither is closed, and neither is owned by any phase below:**

- **Nine command specs claim *"Every mechanical step is a normal Bash tool call to `<cmd>_helper <verb> ...`"*** — `audit:70`, `finalize:50`, `fix:86`, `grill:72`, `report-bug:33`, `spec-check:64`, `summarize:45`, `review:64`, and `verify:57` before its repair. ⚠ **All nine were already FALSE before plan 91 existed**, because `artifact_helper commit-artifacts` has been called from every one of them all along. `verify:57` was repaired here **only** because it carried an explicit exception ENUMERATION whose incompleteness this work deepened; the other eight are blanket claims with no list. Fixing them is one deliberate repo-wide decision, not a side effect of a layout migration — which is why this phase reports them and stops.
- **`_specify/_schema.py:303`'s comment** claims `_group_for_path` *"only ever emits the keys listed here"*. That was **already imprecise before this work**: the function returns the path itself as a private group key for any relative path matching none of its four prefixes. The 2026-08-29 change widened the ways a path can reach that fallback but did not create it.

**Verify**: every site in the inventory above is replaced by a helper call, and every remaining depth-1 spelling in `src/commands` is a **quotation or a prohibition** — named as such at its site — never an instruction the model acts on. ⚠ **Do not write this as "the grep returns nothing"; that is the mistake Phase 1's original Verify made, and this class is worse for it.** No single pattern detects the class: it is spelled at least three ways (`specs/*`, `specs/NNN-*`, and `specs/<token>/` — `/devforge:specify` Phase 0.5's `specs/<resolved-feature-dir>/*-seed.json` matches none of the first two), and one legitimate survivor is guaranteed, since that same block **forbids** globbing `specs/*/` project-wide and must keep quoting the shape it forbids. A test per new verb (test-immediately rule). Each verb resolves a legacy `specs/NNN-slug/` feature today, and the depth branch it inherits from `find_feature_dirs_with` is the same one Phase 3 switches on — so no verb needs re-editing at Phase 3.

**MET 2026-08-29 — with one recorded exception that is the CORRECT outcome, not a miss:**

- **Every site in the inventory is replaced by a helper call, except `/devforge:specify`'s instruction half — and that non-migration is right.** `find-feature-artifacts` always walks **every** feature directory and carries no flag narrowing it to one. Phase 0.5's check exists precisely to scope its lookup to the ONE resolved directory, and the block's own next sentence **forbids** globbing `specs/*/` project-wide. Routing it through the verb would therefore perform, via a helper, the exact project-wide enumeration the block exists to forbid — converting a **mechanical** guarantee into a **model-obeyed** filter. It stays an orchestrator-run glob, and the reason is recorded at the site (`src/commands/specify/main.md:139`), not only in this plan. ⚠ It is **not** a Phase-3 hazard: rooted at the opaque `<feature_dir>` token rather than at `specs/`, it carries no depth assumption to break.
- **The guaranteed legitimate survivor this Verify named turned up exactly where it said it would** — that same block still quotes `specs/*/` as the shape it forbids. That the prediction held is evidence the bar was set correctly; it is not licence to relax it.
- **The `specs/` count in `src/commands` after Phase 1b is 45 occurrences across 14 files**, re-derived on **2026-08-29** with `grep -rho 'specs/' src/commands --include="*.md" | wc -l` — the same method every earlier reading in this document used. ⚠ **Re-derive before quoting.** The figure has moved three times already (388 / 26 → 69 / 17 → 45 / 14) and is an order of magnitude with a method attached, never a constant.
- **Every survivor still falls in one of Phase 1's four named classes**, with class **(b)** now reduced to the single deliberate site above; the rest are (a) bare `specs/` naming no child, (c) transcriptions of literals the helper composes (e.g. `render-plan-handoff`'s invocation line, flagged at its site as the helper's string), and (d) `specs/` meaning the artifact root.
- **Tests accompanied each build increment** (`tests/lib/_artifact/test_find_feature_artifacts.py`, `…_recency.py`, `…_limit.py`). Full suite green — ⚠ and read that exactly as narrowly as the regression above requires: three green Phase-1 suites missed a live defect, so green here means the covered surface did not break, never that nothing did.

### Phase 2 — Ticket identity + `REQUIRE_TICKET` (Python) (D1 = (a) ratified; see Phase 0)

1. `REQUIRE_TICKET` added to `.devforge/project-config.json` and read at every site the rule fires. `_implement/_cmds_commit.py`'s `COMMIT_ATTRIBUTION` handling is the shape precedent for a *documented* key — `:45` and `:113` document it, `:168` names it as a constant, `:197-198` reads it — and is itself a four-site surface inside a single module. Read the ⚠ below before scoping this task.
2. Ticket validator + normalization per OQ-2.
3. `/devforge:configure` asks the question and renders the key.
4. Intake (`/devforge:research`, `/devforge:discover` Phase 4 / Step 4.1) asks for the ticket in the **existing** `AskUserQuestion`, and refuses to allocate when `REQUIRE_TICKET` is true and no valid ticket was given. Attach mode is a no-op arm (OQ-5).
5. **The emitted text states that the rule is discipline, not verification** — that nothing confirms the ticket exists and `PROJ-0000` satisfies it. This is the first of the two obligations D4's 2026-08-29 deliberation creates, and it binds every consumer-facing surface this phase writes: the `/devforge:configure` question in task 3 and the intake prose in task 4. D4 saying it in this plan does not discharge it; the operator reads the emitted docs, not this file.
6. **The refusal in task 4 names both routes out** — supply a valid ticket, or set `REQUIRE_TICKET` to `false` — never a bare refusal. The second of D4's two obligations: a hard fail whose message does not say how to proceed converts rigidity into a dead end.

⚠ **Adding a config key is a multi-file, fail-closed surface — never a one-line addition.** Two config keys shipped in the 24 hours before this plan was last re-verified (2026-08-27), and both are worked examples to model this task on rather than re-derive:

- **`E2E_COMMAND` (plan 90)** reaches four Python modules under `src/devforge/lib/` — `_configure/_render.py`, `_verify/_cli.py`, `_verify/_e2e.py`, `_verify/_verdict.py` — plus `/devforge:configure`'s own prose. Plan 90's record in `CLAUDE.md` calls it *"a SIX-file config surface whose fails-closed-if-missed member is `_cmds_verify.py`'s required-field loop, which violates on any `None` scalar."*
- **`REGRESSION_GATE` (plan 89)** is the second; read its `CLAUDE.md` entry for the surface it actually paid.

The **required-field loop is the named trap**: a key emitted into the config but absent from that loop fails **closed**, at a consumer that never mentions the key by name, so the failure surfaces far from the edit that caused it. Enumerate the full surface — every emitter, every reader, every required-field list, every prose site — and write it down *before* writing any of it. Phase 2's cost estimate is wrong if it assumes otherwise.

**Verify**: a test per new function (test-immediately rule). Round-trip the config through the real producer — `configure_helper render-config` → file → the reader — not a hand-authored fixture. Both `REQUIRE_TICKET` states covered, plus the attach-mode no-op.

### Phase 3 — The layout switch (D1 = (a) ratified; see Phase 0)

Phase 1 makes this possible; it does not make it small. The composition changes in one place, but every resolver has to return **both** shapes from one call across a variable-depth tree — that is the bulk of the work and the whole of the risk (D6, OQ-6).

1. `allocate_feature_dir` composes `specs/<YYYY>/<MM>/<TICKET>/` (`parents=True` already in place at `_shared/feature_alloc.py`'s `mkdir`).
2. `decide_branch_action` emits `spec/<TICKET>` (D5).
3. `next_spec_number` retired; `SPEC_NUMBER_DIR_RE` demoted to legacy-read; `_feature_sort_key` re-based (D6's ordering note).
4. The six resolvers read **both** shapes (OQ-6).
5. The **renderer composition sites** below stop composing the layout (layer 1).
6. The **shell layer** below stops hardcoding depth (layer 3).
7. The **"lowest-numbered feature" contract** below is re-stated at all nine sites (D6's ordering note in prose form, and the one obligation D6's 2026-08-29 deliberation creates).

⚠ **The layout is spelled in THREE layers below the prose, and Phase 1's sweep found all three. This plan named one.** Added 2026-08-28; Phase 3's scope is larger than tasks 1–4 alone describe.

- **Layer 1 — Python that COMPOSES the layout**, not merely describes it. `_specify/_render.py:298` and `:362` both build `specs/{n}-{f}/spec.md`, and `:353` builds `specs/{n}-{f}/handoff.json` in the same block. **Prose cannot fix these; the code must** — which is why they are task 5 here and not Phase 5's docs sweep. They are `.format()` templates with the layout inlined, so they survive any amount of prose editing untouched.
- **Layer 2 — Python docstrings and argparse `--help` text.** Across `_fix/`, `_grill/`, `_verify/`, `_spec_check/`, `_summarize/`, `_implement/`, `_pr_review/`, `_design/`, `breakdown_helper.py` and `plan_helper.py`. ⚠ **The `--help` ones are user-visible**, so they are not documentation in the harmless sense. Phase 5 already claims source-code docstrings, but its paragraph names only `_shared/feature_alloc.py` — **this list widens Phase 5's target set and is the inventory it should work from**. The raw surface is larger than the list: `grep -rl 'specs/' src/devforge/lib` returns **72 files** (method attached, 2026-08-28), most of them legitimate resolver code; the ten modules above are the docstring/`--help` subset the sweep classified out of it.
- **Layer 3 — a shell layer nobody had inventoried.** `src/git-hooks/pre-commit-forcing-functions.sh:54` runs `find "$ROOT/specs" -maxdepth 2 -name "design-manifest.json"` and **skips the check** when nothing matches (`:55-57`). Under the Phase-3 layout a manifest sits at depth 4, so that `find` stops matching and **the hook silently stops gating** — a gate that disarms itself, which plan 90's own record calls worse than no gate. The `-maxdepth 2` is the entire defect; the skip-when-absent behaviour is deliberate and stays.

⚠ **Two structural facts Phase 3 must not rediscover.** Both were established by building Phase 1 and are recorded so Phase 3 does not assume otherwise:

- **`/devforge:specify`'s genuine-fallback arm allocates with NO helper verb.** `specify_helper` has `assign-spec-number` (`_specify/_cli.py:322`) and `assign-feature-name` (`:335`) but **no `allocate-feature-dir`** — that verb exists only on `research_helper` and `discover_helper`. On the genuine-fallback path the creator is a bare `mkdir -p "<feature_dir>"` in the command prose (`src/commands/specify/main.md:837`; `:834` states it creates the directory only on that path). So **"the helper is the sole author of the layout" is NOT true after Phase 1 for that one arm**, and Phase 3's composition change at `allocate_feature_dir` does not reach it. Stated here rather than left for Phase 3 to trip over; this plan proposes no verb for it and takes no decision on whether one should exist.
- **`/devforge:specify` Step 4.1's warm/cold/fallback discriminator is a test on the path INTERIOR.** It asks whether the resolved feature dir's basename *"has the form `<NNN>-<slug>`"* (`src/commands/specify/main.md:542`; the same test seeds `spec_number`/`feature_slug` at `:131`). **No token substitution removes it** — it is not a spelling of the path, it is a question about the path's shape, and the shape is exactly what D6 changes. This is Phase 3's depth-branch problem in prose form, and it is the one place where reading both shapes has to be decided by the orchestrator rather than absorbed by the accessor.

⚠ **The "lowest-numbered feature" contract goes false at nine sites the moment this ships, and nothing mechanical will say so.** Task 7 above; the obligation D6's 2026-08-29 deliberation creates. What resolution actually does on a mixed install: `iter_feature_dirs` emits every legacy dir before every new-shape one (legacy by `NNN`, new-shape by `(YYYY, MM, leaf)`), and `_glob_feature_dirs`'s stable re-sort ties every new-shape leaf at `_feature_sort_key`'s `2**31` — so `/devforge:implement` drains legacy features in `NNN` order first, then new-shape features in allocation-date order. Re-state each site to describe that, rather than deleting the phrase. ⚠ **These are line numbers and line numbers move — re-grep before editing, and use the list to know what to look for, not to navigate blind.**

- `src/CLAUDE.md:101` — `/devforge:implement`'s Command Details entry: the emitted, consumer-facing statement of the contract.
- `src/commands/implement/main.md:27`, `:31`, `:83`, `:89` — the opening paragraph, the `Usage:` line, PHASE 1's instruction line, and the helper-behaviour paragraph. ⚠ `:89` states the feature-level rule and the task-level rule **in one sentence**; only the feature-level half moves.
- `src/devforge/lib/_implement/__init__.py:6` — the package docstring's task-resolution domain line.
- `src/devforge/lib/_implement/_cli.py:49` — `resolve-next-task`'s argparse help text. ⚠ **User-visible**, not documentation in the harmless sense — the same distinction layer 2 above draws.
- `src/devforge/lib/_implement/_cmds_resolve.py:5` — the module docstring; `:120` — `_glob_feature_dirs`'s own docstring, which task 3 edits anyway when `_feature_sort_key` is re-based.

**Four further `lowest-numbered` occurrences in `src/` are TASK-level and must NOT be touched** — task numbering *within* a feature directory is untouched by D6: `_cmds_resolve.py:6`, `:210`, `:255`, and `breakdown_helper.py:3653`. The arithmetic closes, which is how the count of nine is checkable rather than remembered: `grep -rn 'lowest-numbered' src/` returns **13 lines across 6 files** (method attached, 2026-08-29) — nine feature-level, four task-level. `CHANGELOG.md:52` states the contract too and is deliberately excluded: it is a dated historical release entry, not a live claim.

⚠ **Phase 5's sweep would not find these, which is why they are task 7 and not left to it.** Some of the nine also sit in Phase 5's declared target set (`src/CLAUDE.md`; the four `_implement/` docstring-and-`--help` sites, via layer 2 above), but that phase hunts two other sentence classes and its **Verify** greps `NNN-` — and a sentence reading *"the lowest-numbered incomplete feature"* contains neither `specs/` nor `NNN-`. Task 7 owns all nine.

**Verify**: an install containing *both* a legacy `specs/007-old-thing/` and a new `specs/2026/08/PROJ-123/` resolves both from every one of the six consumers, and the pre-commit hook finds a `design-manifest.json` under both. `allocate_feature_dir`'s never-overwrite contract still fails loudly on a collision. The `test_non_nnn_dirs_ignored` pin either still passes or its replacement is written in the same commit.

### Phase 4 — `Run by:` provenance

1. `_specify/_render.py:135` — replace the hardcoded `**Author**: Claude + User` (D8).
2. `_research/_render.py:51-54` — append the line to the existing header block.
3. `plan.md` and `summary.md` — prose instruction, since Python does not render them.
4. The value source, the absent-not-fake rule, and the config gate (D9). Whichever OQ-8 option Phase 0 ratifies gets the same specificity `REQUIRE_TICKET` gets in Phase 2 — a named read site, a `/devforge:configure` question (or an explicit statement that there is none), and a render path.
5. The stated bound sentence — creator only, later edits untracked — in the emitted docs.
6. **Conditional on OQ-7 resolving as "keep the original".** Read the existing `Run by:` line out of the current `spec.md` before re-rendering and thread that value back into `state`. `render_spec` (`_specify/_render.py:118`) is a pure function of `state` with no file read-back today, so without this task a re-render recomputes the value from whatever `git config user.name` returns now and silently violates D9's own creator-only bound. If OQ-7 instead accepts "the last full render wins", this task is dropped and item 5's bound sentence is restated to match.

**Verify**: a test per renderer covering set / unset `git config user.name` and both config states. The unset case asserts the line is **absent**, not empty and not `unknown`. When task 6 is in scope, one further case: a re-render after a grill re-entry keeps the **original** `Run by:` value even when `git config user.name` now returns a different name.

### Phase 5 — Docs + cross-reference sweep

`src/devforge/storage-rules.md` (the layout is described in ~20 places there), `src/CLAUDE.md`, the per-command "Produces" blocks, `CHANGELOG.md` under `## [Unreleased]`, this repository's `CLAUDE.md` active-plan index line, and a `PLAN-STATUS-ARCHIVE.md` entry.

**Source-code docstrings are part of this sweep, not exempt from it** — `src/devforge/lib/_shared/feature_alloc.py`'s 86-line module docstring plus the `next_spec_number` (`:133`) and `allocate_feature_dir` (`:160`) function docstrings. The module docstring asserts the NNN layout as canonical in at least six sentences, among them *"allocate_feature_dir -- creates specs/NNN-slug/ on disk"* (`:34-35`), *"NNN dir-naming constants"* (`:23`) and *"OQ-4 ratified this: NNN is the identity, the slug is a label"* (`:81` — that is **plan 68's** OQ-4, not this plan's) — the last one contradicted outright by F2. This matters more than the prose files do: this plan sends future sessions to that module as the ground truth for how allocation works (see "Verified ground truth" above), so a stale docstring there mis-teaches exactly the reader who followed the instruction.

⚠ **That paragraph names one module; the real docstring surface is ten more.** Phase 1's sweep inventoried them as Phase 3's **layer 2** — read that bullet before scoping this phase, and note that its argparse `--help` half is user-visible text, not documentation in the harmless sense.

Two sentences that become false on this build and must be hunted specifically: anything asserting that a feature directory is an immediate child of `specs/`, and anything asserting `NNN` is the feature identity.

**Verify**: `grep -rn 'NNN-' src/ scripts/` leaves only deliberate legacy-shape references, each adjacent to text saying it is legacy.

### Phase 6 — Consumer e2e — **USER-DRIVEN HARD GATE, not run at build time**

Known-answer anchors:

1. `REQUIRE_TICKET=true`, ticket given → `specs/2026/08/PROJ-123/` + branch `spec/PROJ-123`.
2. `REQUIRE_TICKET=true`, no ticket → intake refuses, **nothing** is created under `specs/`.
3. `REQUIRE_TICKET=false` → the pre-existing behaviour, unchanged.
4. An install carrying a legacy `specs/NNN-slug/` → `/devforge:plan` and `/devforge:implement` still resolve it.
5. `git config user.name` unset → `spec.md` renders with **no** provenance line.

Anchors 1 and 2 are scored as a **pair** — a rule that satisfies 1 by allocating anything at all fails 2.

---

## Non-goals

- Tracker integration of any kind. The ticket is a string; nothing validates its existence (D4).
- Migrating existing `specs/NNN-slug/` directories. They are inert history (plan 68 D3).
- A finalize-time archive, or any other post-creation move. Rejected in "Why".
- A per-edit provenance trail (D9).
- Stamping provenance on task files, bug files, or the twenty other artifacts with header blocks (D7).
- Changing `bugs/NNN-*.md` naming (OQ-4 recommendation).
- Any new `verify-*` PHASE-3.5 gate number. Plan 75's tripwire holds everywhere except D4's declared exception.

---

## Context for next session

- The expensive part of this work was **not** the layout. It was that `specs/…` was a literal hand-composed in **388 places across 298 lines in 26 command specs** in nine spellings, while `allocate_feature_dir` had been returning the full `path` all along. **That cost is PAID — Phase 1 shipped 2026-08-28 taking the figure to 69 across 17 files, and Phase 1b shipped 2026-08-29 taking it to 45 across 14**, every survivor in one of four named classes. Both the 388 and the 69 are history; quoting either to argue the cost of a later phase is wrong. Re-derive, do not quote. Read D1 anyway — it is why the sweep came first.
- `**Author**: Claude + User` at `_specify/_render.py:135` is the only `**Author**` in **production renderer code** (`src/`; `tests/` fixtures and one `done-plans/` file carry the string too) and it names nobody. F3 replaces a lie; it does not add a field.
- The maintainer's drift objection (quoted in "Why") is the load-bearing reason this plan has no archive step. Do not re-propose one without answering it.
- D4 knowingly breaks half of plan 75's tripwire. That is declared, not overlooked — and on 2026-08-28 it was ratified by directive with the deliberation it demanded **not** performed. **That deliberation was performed 2026-08-29 and D4 UPHELD, narrowly**, handing Phase 2 two obligations (tasks 5 and 6: say the rule is discipline not verification, and name both routes out of the refusal). Read D4 and `## Phase 0 close record` before building Phase 2. **D6's deliberation was performed the same day and D6 UPHELD too — but on a WEAKER footing: it stands because D2 and D3 entail it, not on its own merits**, handing Phase 3 one obligation (task 7: re-state the "lowest-numbered feature" contract at all nine sites). Read D6 before building Phase 3 — its closure is recorded in D6's own ⚠ only, and `## Phase 0 close record`'s D6 lines are stale on that point.
- **Phases 1 and 1b are built (2026-08-28 and 2026-08-29) and PHASE 2 is where you resume.** Phase 0 closed and Phase 1 shipped on the same day; Phase 1b shipped the next. Phase 2 and everything after have not started. Both built phases are **build-verified only — NOT consumer-validated**: no install has been run against either, so read no shipped behaviour here as confirmed by use. The **Status** field at the top of this file is the authority.
- **Phase 1b fixed a REGRESSION Phase 1 introduced, and the lesson generalizes past this plan.** A prose-only token substitution changed a Python classifier's input from relative to absolute and silently broke source-origin tagging; **three full green suites did not notice, because nothing covered it.** Phase 3 is a far larger version of the same manoeuvre. Read Phase 1b's build record before starting it, and treat "the suite is green" as evidence about the covered surface only.
- **The two Phase-1 reports are now CLOSED** (`324942c`) — the `/devforge:grill` skeleton's em-dash ruled in the renderer's favour, and `crash-recovery.md:7`'s prose ruled wrong and corrected. ⚠ Phase 1's defect harvest still quotes the old `crash-recovery.md` wording verbatim and **that string no longer exists in the tree**; the harvest is kept as a historical record with dated repaired-notes beneath it. ⚠ `write_wip_marker` is **still production-unreachable** — the report was closed by fixing the claim, not the reachability.
- **Two findings are open, both recorded by Phase 1b and owned by no phase below** — nine command specs' blanket *"Every mechanical step is a normal Bash tool call to `<cmd>_helper …`"* claim (already false before this plan, since `artifact_helper commit-artifacts` has always been called from all nine), and `_specify/_schema.py:303`'s over-precise comment about `_group_for_path`'s key set. Both are reported, neither is fixed; the first needs one deliberate repo-wide decision.

## When resuming work

1. Read this file end to end, then `CLAUDE.md`'s active-plan index for plans 68, 75, 87 and 88 — each constrains a decision here — plus 85 (it made `/devforge:grill` mandatory to run, which raises OQ-5's likelihood), and 89 and 90 (the two worked config-key examples Phase 2 models on).
2. **D1 is answered — (a)**, ratified 2026-08-28. Every phase shape below it depends on that answer and Phases 1–3 are written for it, so read `## Phase 0 close record` — including its three caveats — before re-opening it or before starting Phase 2 or Phase 3.
3. **Do not trust the counts in "Verified ground truth" — they are PRE-SWEEP and the builds invalidated them twice.** They were taken 2026-08-26, re-taken 2026-08-27 (they moved in that one-day gap, in which four plans landed), superseded on 2026-08-28 when Phase 1 took them 388 → 69, and superseded again on 2026-08-29 when Phase 1b took them 69 → 45 across 14 files. They are preserved as the baseline the plan was argued against, marked as such in place. Re-grep for a current figure; the method is attached to every reading.
4. Follow the repository's working process: draft the step, argue it, get alignment, then build. Route markdown edits through `instruction-author` → `instruction-reviewer`; Python through `python-engineer` → `python-reviewer`, with a test written and run in the same turn as every function.
