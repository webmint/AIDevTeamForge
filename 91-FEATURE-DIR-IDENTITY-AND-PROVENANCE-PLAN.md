# 91 — Feature-directory identity + artifact provenance

**Status**: NOT STARTED — awaiting Phase-0 ratification (D1–D9 + OQ-1–OQ-8).
**Created**: 2026-08-26
**Branch**: `develop-2.0-init`
**Origin**: maintainer design conversation 2026-08-26 (no incident, none claimed). Two problems raised together and deliberately kept separate below: *identity* (a feature directory's name carries no external meaning) and *volume* (a flat `specs/` accumulates unboundedly over a multi-year, multi-dev project).

---

## Why

Today a feature directory is `specs/NNN-<slug>/`, where `NNN` is a repo-local sequential counter allocated by scanning `specs/` (`_shared/feature_alloc.py`). Three consequences the maintainer named:

1. **`NNN` means nothing outside this repo.** The framework already knows about tickets — `_implement/_cmds_commit.py:127` scrapes `[A-Z]+-[0-9]+` out of a *source* branch in wrapper mode — but it never asks for one, so in standalone mode the ticket is unknown. `/devforge:finalize` cannot compose `[PROJ-123] - Description` there either, though for a separate reason: that format is gated on wrapper mode, not on knowing a ticket (see D5).
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
| **F1** | The feature-directory path becomes **opaque**: the helper is the only author of the layout; command prose receives a path and never composes one. | Python + 386 prose occurrences |
| **F2** | Identity becomes the **ticket**; layout becomes `specs/YYYY/MM/TICKET/`; `REQUIRE_TICKET` gates intake. | Python (composition + six variable-depth resolvers) + intake prose |
| **F3** | A **`Run by:`** provenance line on the artifacts that travel outside the repository. | Python (2 renderers) + prose (2 artifacts) |

F1 is the enabling refactor: it exists so that F2 — and the *next* layout change after F2, which there will be — is paid inside the helper plus its resolvers instead of across 386 prose occurrences. It does **not** make the resolver work cheap; see D1 and Phase 3.

---

## Verified ground truth

Everything below was read from the tree on 2026-08-26. Cited so a future session does not re-derive it, and does not trust it blindly either — re-grep before acting.

### The layout is authored in two places at once

- `_shared/feature_alloc.py:101` — `SPECS_ROOT_DEFAULT = "specs"`.
- `_shared/feature_alloc.py:122` — `SPEC_NUMBER_DIR_RE = re.compile(r"^(\d{3})-(.+)$")`. **Exactly three digits**, deliberately not widened; pinned by `tests/lib/_shared/test_feature_alloc.py::test_non_nnn_dirs_ignored`.
- `_shared/feature_alloc.py:99` — `FEATURE_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+){1,3}$")` — 2–4 lowercase kebab segments.
- `_shared/feature_alloc.py:125` — `_SPEC_BRANCH_PREFIX = "spec/"`.
- `allocate_feature_dir` **already returns the full path** (`"path"`, alongside `number` / `formatted_number` / `slug` / `dirname` / `created`).

And yet the command specs rebuild that same path by hand. Raw occurrence counts across `src/commands/**/*.md`, recounted 2026-08-26 with one consistent method — `grep -rho 'specs/' src/commands --include="*.md" | wc -l`:

```
117 × specs/<NNN-slug>        28 × specs/<feature>       12 × specs/<NNN>-<feature-name>
100 × specs/[feature]         27 × specs/<dirname>        8 × specs/<NNN>-<slug>
 32 × specs/                  24 × specs/*                6 × specs/<NNN>-<feature>
 20 × specs/NNN-*             + smaller variants
```

The named shapes above sum to 374 and the smaller variants carry the remaining 12, so the table totals 386 under that same method.

**386 raw occurrences across 296 matching lines in 25 command-spec files, in at least nine different spellings.** This — not directory depth — is what makes any layout change expensive. Phase 0 re-derives the figure with the command above; counting *lines* instead of occurrences yields 296 and is not the number this plan is scoped against.

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
- `plan.md` and `summary.md` are **LLM-authored prose** — no Python renders either one. The two differ downstream: `plan.md` is *parsed* by `plan_helper.py` (`:83` documents the `finalize-handoff` verb, `:2136` is `cmd_finalize_handoff`), while `summary.md` is neither rendered nor parsed by any Python in this repository. A stamp on either is an instruction change, not Python.
- **Zero** reads of `git config user.name` anywhere in `src/devforge/lib/`. There is no identity source in the framework today.
- `_configure/_render.py:54`, `:80` — `COMMIT_ATTRIBUTION` is a *derived* config key, emitted only when `ai_attribution == "Yes"`. The framework already asks the operator whether attribution may be written into files.
- **20 modules** write `**Status**:` / `**Created**:` / `**Date**:` header lines. There is **no shared header composer**. "Every artifact carries a label" would therefore be 20 touch points plus a test each.

### Adjacent facts that constrain this plan

- The research / specify / discover handoff schemas carry **no** `feature_dir` or `path` key (grep-verified). The layout is not baked into the JSON contracts, so changing it does not stale a stored path. *Phase 0 re-confirms this before Phase 3 relies on it.*
- Plan 68 D3 set the precedent that legacy intake directories are **inert history — nothing migrates them**. This plan follows it (D6).
- Plan 68 D6 attach mode: a `/devforge:grill` RE-ENTER-UPSTREAM seed reuses an existing feature directory and **skips allocation entirely**. Any allocation-time rule must therefore have an attach-mode arm that is a deliberate no-op.
- Plan 87 (artifact language guard) and plan 78 (test identifier scrub) both exist because artifacts are committed and this repository is public. F3 adds a real human name to committed files and must be weighed against that, not around it.
- Plan 88 (cold-fix bugs lane — **Phases 0–4 BUILT 2026-08-26; Phase 5 consumer e2e NOT run**) owns `bugs/NNN-*.md`. Whether `REQUIRE_TICKET` reaches bug files is OQ-4. ⚠ Status refreshed 2026-08-26; OQ-4's substance is unaffected — plan 88 did NOT change bug-file naming, so its recommendation still stands as written.

---

## Decisions to ratify (D1–D9)

D2, D3, D5, D7, D8 and D9 were argued and settled in the originating conversation; they are listed anyway because Phase 0 is where a decision becomes binding in this repository. **D1 is genuinely unanswered** and must be settled first — it changes the shape of every phase after it.

That leaves **D4 and D6**, which belong to neither bucket and must not be waved through by omission:

- **D4 was PARTIALLY argued.** The maintainer agreed to the `REQUIRE_TICKET`-as-per-install-policy-key *shape*. The tripwire break that shape carries (D4's ⚠) was never put to them as a decision, so D4 requires full Phase-0 deliberation.
- **D6 was NOT argued at all.** It retires `NNN` as the feature identity and never came up in the originating conversation. It requires full Phase-0 deliberation.

### D1 — Sequence: opaque path first, or layout first? **UNANSWERED**

- **(a) F1 first (RECOMMENDED).** Make the helper the sole author of the path, retire the 386 hand-composed occurrences, *then* change the layout inside the helper. Cost: the prose sweep is paid once, up front, before any user-visible behaviour changes.
- **(b) Layout first.** Ship `specs/YYYY/MM/TICKET/` directly. Cost: 386 prose occurrences edited now, and 386 again the next time the layout changes — and this conversation produced three candidate layouts in one sitting, so a next time should be assumed, not hoped against.

The whole argument for (a) is that **the prose sweep is paid once instead of twice**. It is not that (a) makes the layout switch cheap: under either ordering, Phase 3 still has to teach six resolvers a variable-depth walk that returns both the legacy and the new shape (see Phase 1's ⚠ and Phase 3). No ordering makes that work disappear, and this plan does not claim it does.

Recommendation (a). The counter-argument is honest and recorded: (a) delivers **nothing the maintainer asked for** in its first phase, and a refactor whose payoff is entirely in the next phase is the kind that gets abandoned half-done. If (a) is ratified, Phase 1 must therefore be independently valuable — it is: it removes a nine-spelling literal from 25 files, which is a real hallucination surface today regardless of any layout change.

⚠ Phases 1, 2 and 3 below are written for (a). Ratifying **(b)** requires restructuring Phases 1–3 *before* any build starts — this document provides no alternate structure for it.

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

### D4 — Ticket mandatory, via `REQUIRE_TICKET` in `.devforge/project-config.json` — **PARTIALLY ARGUED**

"No ticket, no spec" as a **mechanical** trigger — no severity threshold, no judgment call, matching the zero-escape-hatch policy. But it is a **per-install policy key**, not a framework invariant, for two reasons:

1. **It is discipline, not verification.** The framework has no tracker integration and cannot confirm a ticket exists. `PROJ-0000` satisfies the rule with fake traceability. The emitted docs must say this plainly; a future session must not read the gate as a guarantee.
2. **It locks out installs with no tracker — including this repository**, whose own plans are `NN-TOPIC-PLAN.md` at the repo root.

`WORKSPACE_MODE` and `COMMIT_ATTRIBUTION` already live in `project-config.json`; this key joins them. At runtime the rule is binary — the escape hatch is closed at run time and the policy is chosen once, at configure time.

⚠ **This is the one place the plan deliberately breaks plan 75's tripwire** ("no new check number AND no new unnumbered hard-fail validator"). `REQUIRE_TICKET=true` *is* a new unnumbered hard-fail validator at intake. Declared here rather than smuggled: it is the mechanism the maintainer asked for, it is opt-in per install, and it adds no `verify-*` gate number to any PHASE-3.5 sequence. Everything else in this plan holds the tripwire.

### D5 — Branch name is `spec/TICKET` — RATIFIED IN CONVERSATION 2026-08-26

`spec/PROJ-123`, not `spec/2026/08/PROJ-123` (slashes are legal in git refs but buy nothing here).

⚠ **There is no free consequence here. Standalone `[PROJ-123] - Description` is NOT built by this plan and stays a known gap.** An earlier draft of this decision claimed the branch rename would hand `/devforge:finalize` the bracket format in standalone mode for the first time. It does not: that format is gated on **mode**, never on whether a ticket is extractable. `_implement/_cmds_commit.py:488-499` sets `ticket_id = ""` on the standalone arm — the ticket is never extracted there at all — and `_compose_message` (`:225-233`) emits `"[{ticket_id}] - {title}"` only `if is_wrapper`. `src/commands/finalize/main.md:201-202` says the same independently: the bracket format is labelled *"Source repo (wrapper mode only)"*, and standalone has no source repo. Closing that gap would mean making the gate ticket-driven rather than mode-driven in **both** `_cmds_commit.py` and `finalize/main.md`'s message-composition instructions — recorded here as out of scope, not as planned work.

### D6 — `NNN` is retired; both shapes coexist forever — **NOT ARGUED**

`next_spec_number` becomes dead, `SPEC_NUMBER_DIR_RE` becomes a *legacy-read* pattern, and `_feature_sort_key`'s `^(\d+)` no longer matches anything newly written.

**No migration** (plan 68 D3 precedent). Existing installs keep `specs/NNN-slug/` forever. Resolution must therefore **read both shapes and write only the new one**. This is the single largest correctness risk in the plan and Phase 3's **Verify** line is built around it.

Note the ordering consequence: sorting by ticket number is only *approximately* chronological, and interleaves across tracker prefixes (`ENG-*` vs `PROJ-*`). Any code that today relies on `NNN` for ordering must be re-examined rather than mechanically ported.

### D7 — Provenance stamp: `Run by:`, on travelling artifacts only

Four artifacts: `spec.md`, `plan.md`, `summary.md`, `research-report.md` — the ones that get pasted into PRs, tickets and Obsidian, where git metadata does not follow.

**Not** task files: they never leave the repository, and stamping 40 of them per feature pays 40× for nothing.

**Named `Run by:`, not `Author:`.** The document is composed by the model and approved by the human; a field named `Author` on a document whose author wrote none of it misleads exactly where accountability matters. A future reader must be able to tell "who ran this" from "who decided this".

### D8 — `**Author**: Claude + User` (`_specify/_render.py:135`) is REPLACED, not supplemented

One provenance line per artifact. Two adjacent lines, one of which is a constant that names nobody, is worse than either alone.

### D9 — The stamp is config-gated and never invented

- Value source: `git config user.name`, captured at **creation** time.
- Unset / unavailable → the line is **absent**. Never `unknown`, never a placeholder. A fake value is worse than no value.
- **Config-gated.** An install that answered "no attribution in files" must not get a real human name stamped into them by another route (`_configure/_render.py:80`). *Which* gate carries that — the existing `ai_attribution` answer, or a new key of its own — is **OQ-8**; nothing in this plan presumes a new key exists.
- The emitted text must state the bound: the field records the **creator**, and later edits (grill re-entry rewriting `spec.md`, `**Status**:` flips) do **not** update it. Without that sentence the field becomes exactly the "used to be true, now silently false" failure mode `CLAUDE.md` names as most dangerous. **A per-edit trail is explicitly NOT built** — that is `git log --follow` reimplemented in markdown inside a git-tracked file.

---

## Open questions (OQ-1 – OQ-8)

- **OQ-1 — `REQUIRE_TICKET` default.** `false` (opt-in) or `true` (opt-out)? Note this repository needs `false`. Recommendation: default `false`, and let `/devforge:configure` ask, defaulting to `true` when `WORKSPACE_MODE` is wrapper (wrapper mode implies an external tracker by construction).
- **OQ-2 — Ticket format and letter case.** Constrain to `[A-Z]+-[0-9]+` (matching `_TICKET_PATTERN`, so the framework has one ticket notion rather than two), or accept free-form? And: an uppercase directory name is new — `FEATURE_NAME_RE`'s lowercase-only convention dies with the slug. ⚠ On a case-insensitive filesystem (macOS default) `PROJ-123` and `proj-123` collide while on Linux they do not; whichever is chosen must be **normalized at allocation**, not left to the typist.
- **OQ-3 — Bucket source.** `YYYY/MM` from the allocation date — confirm, and confirm the timezone/clock source (local date, as `set-date` already enforces `YYYY-MM-DD` elsewhere).
- **OQ-4 — Does `REQUIRE_TICKET` reach `bugs/NNN-*.md`?** Plan 88 (**Phases 0–4 BUILT 2026-08-26**; status refreshed the same day) makes bug files a `/devforge:fix` input — that input is now shipped, not prospective. Recommendation: **no** — bug files are not features, keep them `bugs/NNN-slug.md`, and record that as a stated boundary so plan 88 is not silently constrained by this one. ⚠ The recommendation is UNCHANGED by plan 88 shipping: it built no naming change, and its cold lane resolves a bug file by the path the user types, so a rename would break a user-facing argument form.
- **OQ-5 — Attach mode.** A `/devforge:grill` re-entry reuses an existing directory and skips allocation (plan 68 D6). Confirm the ticket rule is a **no-op** there, and that the ticket is recovered from the path rather than re-asked.
- **OQ-6 — Legacy read surface.** Which of the six depth-1 resolvers must read the legacy `specs/NNN-slug/` shape, and which may drop it? Recommendation: **all six read both** — a resolver that silently stops seeing an old feature is a data-loss-shaped bug, not a cleanup.
- **OQ-7 — Re-render behaviour.** When `/devforge:specify` rewrites `spec.md` on a grill re-entry, does `Run by:` keep the original value or take the current one? D9 says creator, so: **keep the original** — which means the re-render must *read back* the existing value rather than recompute it. Confirm this is worth the complexity, or accept "the last full render wins" with the bound stated. Whichever way this lands decides whether Phase 4's task 6 is in scope — `render_spec` (`_specify/_render.py:118`) is a pure function of `state` with no file read-back today, so "keep the original" is a real code change and not a free property.
- **OQ-8 — Which config key gates the `Run by:` stamp?** D9 requires a gate and names none; no such key exists today. **(i) No new key — the stamp rides the existing `ai_attribution` answer directly (RECOMMENDED)**: one fewer key, and the two semantics are close enough that a second toggle mostly invites a pair of settings that contradict each other. **(ii) A new named key**, defaulting from the `ai_attribution` answer. Whichever is ratified must reach Phase 4 with the same specificity `REQUIRE_TICKET` gets in Phase 2 — a named read site, a `/devforge:configure` question (or an explicit statement that there is none), and a render path.

---

## Phases

Each phase must leave the tree buildable and the suite green.

### Phase 0 — Ratification

Settle D1–D9 and OQ-1–OQ-8. Re-verify the two facts this plan leans on hardest before any code moves: the 386 prose-occurrence count (re-derive it with `grep -rho 'specs/' src/commands --include="*.md" | wc -l`, the same method that produced the figure), and the absence of a `feature_dir`/`path` key in the handoff schemas.

**Verify**: every D and OQ has a recorded answer in this file; no phase below has started.

### Phase 1 — Opaque `feature_dir` (gated on D1 = (a))

The helper becomes the sole author of the layout. Command prose stops containing the literal `specs/`.

1. A single resolution accessor, in `_shared/feature_alloc.py` alongside `allocate_feature_dir`, that returns a feature directory path given a feature reference — covering both the allocate path and the resolve path (the six depth-1 consumers).
2. `allocate-feature-dir`'s stdout keeps `path` as the value callers use; `dirname` / `number` / `formatted_number` become **legacy-only** keys (still emitted for the un-migrated shape, not consumed by new prose).
3. Sweep the 386 prose occurrences in the 25 command-spec files onto `<feature_dir>` — the value the helper handed the orchestrator — so that no command spec knows what is inside the path.

⚠ **Build the accessor for a variable-depth tree from the start.** The legacy shape `specs/NNN-slug/` is **one** level below `specs/`; the shape D2 introduces, `specs/YYYY/MM/TICKET/`, is **three**. All six of today's consumers do a single flat scan of `specs/`, and under the new layout a flat scan enumerates *year* directories — it cannot see a new-shape feature directory at all. Reading both shapes is therefore a genuine algorithmic branch dispatched on shape, not a regex swap. An accessor written here as a straightforward flat `iterdir()` will satisfy Phase 1's own Verify (only the legacy shape exists yet) and then need rewriting at Phase 3; put the depth branch in now, with the legacy arm as the only one that currently returns anything.

**Verify**: `grep -rn 'specs/' src/commands --include="*.md"` returns only (a) `storage-rules`-style *descriptions* of the layout, and (b) nothing that instructs the model to compose a path. Full suite green. No behaviour change is visible to a consumer — the same directories are created at the same locations.

### Phase 2 — Ticket identity + `REQUIRE_TICKET` (Python) (assumes D1 = (a); see Phase 0)

1. `REQUIRE_TICKET` read from `.devforge/project-config.json` (join the existing readers; `_implement/_cmds_commit.py:85` is the shape precedent for a documented key).
2. Ticket validator + normalization per OQ-2.
3. `/devforge:configure` asks the question and renders the key.
4. Intake (`/devforge:research`, `/devforge:discover` Phase 4 / Step 4.1) asks for the ticket in the **existing** `AskUserQuestion`, and refuses to allocate when `REQUIRE_TICKET` is true and no valid ticket was given. Attach mode is a no-op arm (OQ-5).

**Verify**: a test per new function (test-immediately rule). Round-trip the config through the real producer — `configure_helper render-config` → file → the reader — not a hand-authored fixture. Both `REQUIRE_TICKET` states covered, plus the attach-mode no-op.

### Phase 3 — The layout switch (assumes D1 = (a); see Phase 0)

Phase 1 makes this possible; it does not make it small. The composition changes in one place, but every resolver has to return **both** shapes from one call across a variable-depth tree — that is the bulk of the work and the whole of the risk (D6, OQ-6).

1. `allocate_feature_dir` composes `specs/<YYYY>/<MM>/<TICKET>/` (`parents=True` already in place at `_shared/feature_alloc.py`'s `mkdir`).
2. `decide_branch_action` emits `spec/<TICKET>` (D5).
3. `next_spec_number` retired; `SPEC_NUMBER_DIR_RE` demoted to legacy-read; `_feature_sort_key` re-based (D6's ordering note).
4. The six resolvers read **both** shapes (OQ-6).

**Verify**: an install containing *both* a legacy `specs/007-old-thing/` and a new `specs/2026/08/PROJ-123/` resolves both from every one of the six consumers. `allocate_feature_dir`'s never-overwrite contract still fails loudly on a collision. The `test_non_nnn_dirs_ignored` pin either still passes or its replacement is written in the same commit.

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

**Source-code docstrings are part of this sweep, not exempt from it** — `src/devforge/lib/_shared/feature_alloc.py`'s 86-line module docstring plus the `next_spec_number` (`:135`) and `allocate_feature_dir` (`:162`) function docstrings. The module docstring asserts the NNN layout as canonical in at least six sentences, among them *"allocate_feature_dir -- creates specs/NNN-slug/ on disk"* (`:34-35`), *"NNN dir-naming constants"* (`:23`) and *"OQ-4 ratified this: NNN is the identity, the slug is a label"* (`:81` — that is **plan 68's** OQ-4, not this plan's) — the last one contradicted outright by F2. This matters more than the prose files do: this plan sends future sessions to that module as the ground truth for how allocation works (see "Verified ground truth" above), so a stale docstring there mis-teaches exactly the reader who followed the instruction.

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

- The expensive part of this work is **not** the layout. It is that `specs/…` is a literal hand-composed in **386 places across 296 lines in 25 command specs** in nine spellings, while `allocate_feature_dir` has been returning the full `path` all along. If you read only one thing before starting, read D1.
- `**Author**: Claude + User` at `_specify/_render.py:135` is the only `**Author**` in **production renderer code** (`src/`; `tests/` fixtures and one `done-plans/` file carry the string too) and it names nobody. F3 replaces a lie; it does not add a field.
- The maintainer's drift objection (quoted in "Why") is the load-bearing reason this plan has no archive step. Do not re-propose one without answering it.
- D4 knowingly breaks half of plan 75's tripwire. That is declared, not overlooked.
- Nothing in this plan has been built. No phase has started. The **Status** field at the top of this file is the authority.

## When resuming work

1. Read this file end to end, then `CLAUDE.md`'s active-plan index for plans 68, 75, 87 and 88 — each constrains a decision here.
2. Answer **D1 first**. Every phase shape below it depends on the answer.
3. Re-grep the two counts in "Verified ground truth" before trusting them; they were taken on 2026-08-26 and the tree moves.
4. Follow the repository's working process: draft the step, argue it, get alignment, then build. Route markdown edits through `instruction-author` → `instruction-reviewer`; Python through `python-engineer` → `python-reviewer`, with a test written and run in the same turn as every function.
