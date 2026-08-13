# 78 — Test-Fixture Client-Identifier Scrub + Recurrence Guard

**Status:** **NOT STARTED — awaiting Phase-0 ratification.** Everything below is a proposal except the two items explicitly marked as already-completed working-tree work (the first substitution pass, and the in-flight follow-up pass) and the one maintainer disposition marked RATIFIED. Nothing else here is settled.
**Branch:** `develop-2.0-init`
**Origin:** A 2026-08-12 review of this PUBLIC repository found identifiers belonging to a private client codebase in tracked test fixtures. The first scrub pass was verified with a grep that returned zero hits and was still incomplete — that failure mode, not the identifiers themselves, is what this plan is shaped around.

## ABSOLUTE CONSTRAINT ON THIS FILE

**This plan is ABOUT client identifiers and must never CONTAIN one.** No real ticket ID, commit SHA, company name, product name, repository name, source symbol, component name, package name, developer name, or client absolute path appears anywhere below — not as an example, not in a table, not in a grep pattern. Identifiers are named by CLASS only ("a ticket-ID-shaped token of the form `LETTERS-DIGITS`", "two commit-SHA-shaped hex strings").

Every executable grep or match pattern this plan calls for must have its **values supplied at execution time from a list held outside this repository**. The reason is structural, not stylistic: **a scrub plan that embeds the identifier list in the repo re-introduces the exact leak it exists to remove**, and does so in a file whose stated purpose guarantees it will be read. This constraint is a design decision, not a formatting preference — see D3.

This repo currently has a policy exempting plan documents from scrubbing. **That exemption is the root cause of the present situation and this file does not rely on it.** This plan is written as though no exemption exists. It also declines to write the maintainer's own test-harness project name (OQ-1's subject), so that the file stays correct under either OQ-1 answer.

## Context for next session

### The measured state (dated snapshot — re-measure before acting, do not treat as permanent)

Measured 2026-08-12. Counts are of files containing client identifiers and of individual hits:

| Area | Files with client identifiers | Hits |
|---|---|---|
| `src/` | 0 | 0 |
| `scripts/` | 0 | 0 |
| `docs/` | 0 | 0 |
| `tests/` | 2 tracked | 36 |
| `done-plans/` | 22 | 146 |
| repo root (plan docs etc.) | 14 | 70 |

**Shipped code and generated documentation are clean.** The exposure is concentrated in plan documents and a small number of test files. This shape matters: it means the fix does not touch what the framework ships to consumers.

### Maintainer disposition — RATIFIED, record as settled

Plan documents and `done-plans/` will be **DELETED at the official v2 go-live** rather than scrubbed. **This plan therefore scopes to tests only.**

**The honest limitation of that disposition, stated plainly:** deleting a file does not remove it from git history. On a public repository, every historical version of every deleted document remains retrievable by anyone who clones. Deletion removes the artifacts from the working tree and from the impression a casual reader forms; it does not reduce what a determined reader can retrieve. **History remediation is a separate decision and is routed out of this plan — no history rewrite is proposed, designed, or scoped here** (see Non-goals).

### The test-file scope — three files

1. A tracked research-helper test file — the largest single concentration.
2. A tracked research handoff-schema test file — **newly discovered; covered by none of the work done so far.**
3. An untracked discover absence-probe test file, created recently.

**Work ALREADY COMPLETED in the working tree (do not re-propose it):**
- Four identifier classes were substituted with synthetic equivalents across files 1 and 3: a source symbol, a product/feature name, a component name, and a ticket ID. The full test suite passed afterward.
- A follow-up pass is **in flight** covering two commit-SHA-shaped hex strings (one a prefix of the other — they survived the first substitution) and a package-name prefix that reused the client's real naming convention.

**Work REMAINING:** file 2 entirely; verification that files 1 and 3 are actually clean once the in-flight pass lands; and a recurrence guard.

### The lesson that shapes every phase below

The first pass was verified by grepping the four substituted tokens. It returned zero hits. It was still incomplete, because two real commit SHAs were never in the substitution table. **The verification confirmed the substitutions; it did not establish the absence of client data.** Worse, the surviving SHAs functioned as a **de-anonymization key** — other files in this repo pair those SHAs with the identifiers that had been replaced, so a reader with both could reverse the entire substitution.

Two consequences the design must encode, not merely mention:

1. **Verification runs against an identifier INVENTORY, never against the substitution table.** A grep that searches only for what you replaced is incapable of finding what you missed. This is why Phase 1 (build the inventory) precedes Phase 2 (substitute) — inverting that order reproduces the original failure.
2. **Partial scrubbing can be worse than none, because it looks complete.** A phase that leaves a join key in place has not reduced exposure; it has concealed the fact that exposure remains. Any phase whose output is "mostly clean" must be reported as NOT DONE.

### Applying this repo's own verification standard

The standard is: **does the artifact look visibly wrong when the work was not done?** A green grep does not meet that bar when the pattern is derived from the fix. Honest assessment of what can and cannot meet it here:

- **Meets the bar — exhaustive literal enumeration.** Parse each affected `.py` file with `ast`, extract *every* string constant, and require an explicit per-literal disposition. You cannot omit what you enumerate exhaustively; the residual risk collapses from *omission* to *misclassification*, and an undispositioned literal is visibly a hole in the artifact. This is the primary instrument. (`ast`-based source analysis is already the technique `scripts/lib/agent_reachability.py` uses in this repo — verified 2026-08-12 — so it is a precedent, not an invention.)
- **Meets the bar for shape-bearing classes — the shape scan.** Commit SHAs, ticket IDs, and absolute filesystem paths have distinguishing shapes, so a shape check fails on an identifier *nobody listed*. This is exactly the class that survived the first pass, which is the strongest available evidence that the shape arm is the load-bearing one.
- **Does NOT meet the bar — name classes.** A company name, product name, component name, boolean prop name, or package prefix has no distinguishing shape. Nothing mechanical detects them. The only instrument is the human-authored inventory, whose completeness is **asserted, not proven**. Say this in every artifact the work produces rather than letting a green run imply more than it establishes.

## Decisions (ratify at Phase 0 — none is settled)

- **D1 — scope is `tests/` only.** Follows the ratified deletion disposition. `src/`, `scripts/`, `docs/` are measured clean and are not touched (unless OQ-1 resolves otherwise, which is the only path that reaches `src/`).
- **D2 — inventory-first ordering is mandatory, not preferred.** Phase 1 produces the inventory before Phase 2 changes any file. A substitution performed before the inventory exists can only ever be verified against itself, which is the documented failure. This ordering is the plan's spine; reordering it defeats the plan.
- **D3 — the real-identifier inventory lives OUTSIDE this repository; the SYNTHETIC allowlist lives INSIDE it.** This inversion is the key design move. The inventory of real client values is unpublishable by definition, so it cannot be committed, cannot be gitignored-but-present (an ignore-rule edit or a `git add -f` re-exposes it), and must be referenced by a path outside the working tree — proposed via an environment variable, resolved at execution time. The **allowlist of approved synthetic values is publishable precisely because it contains no client data**, so it ships in-repo and is the artifact the mechanical guard checks against. Consequence: the guard asks "is every shape-bearing literal a *declared synthetic*?" — a question answerable entirely from public data — rather than "does any literal match a real identifier?", which would require the secret in-repo.
- **D4 — an absent inventory must produce a LOUD SKIP, never a pass.** Any check that silently degrades to green when its list is unavailable is worse than no check, because it manufactures false assurance in exactly the situation where assurance is least warranted. The check announces SKIPPED on stdout and the exit code reflects that it did not run.
- **D5 — the guard is a `scripts/lib/` module + a `scripts/` CLI + a pytest test against the live tree**, mirroring plan 41's shape exactly (`scripts/lib/agent_reachability.py` + `scripts/verify-agent-reachability.py` + `tests/lib/test_agent_reachability.py` — all three verified present 2026-08-12). Rationale in Guard options below.
- **D6 — hard-fail on undeclared shape-bearing literals; ADVISORY report on name-shaped literals.** The advisory arm gates nothing and catches nothing by itself; it is a prompt for a human. Labeling it as anything stronger would overclaim. A future session must not "strengthen" the advisory arm into a gate without first solving the false-positive problem measured in Phase 4.
- **D7 — synthetic replacements preserve SHAPE and discard VALUE.** Verified against file 2 on 2026-08-12: several fixture values are load-bearing for their assertion — a SHA-shaped field is rejected by the schema unless it is hex and of minimum length; a summary string must match a literal-replacement regex to trigger the code path under test; an identifier must appear twice to exercise duplicate detection. So "make it obviously fake" cannot mean "make it arbitrary". The rule is: preserve every property the assertion depends on (character class, length, token ordering, repetition), discard everything that carries meaning about the client.
- **D8 — a surviving JOIN KEY means the file is NOT done.** The inventory records, per identifier, whether that value appears elsewhere in the repo paired with an already-substituted identifier. A file with zero remaining listed identifiers but one surviving join key is reported NOT DONE, not "clean with a caveat" (per the lesson's consequence 2).

## Guard options weighed

- **Option A — a test in the existing suite.** Runs on every `pytest` invocation with no new infrastructure. This repo has **no CI config, no Makefile, and no pytest config file** (verified 2026-08-12: no `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`, or `Makefile` at repo root), so a pytest test against the live tree is the only mechanism here that runs automatically. Plan 41 reached the same conclusion for the same reason.
- **Option B — the opt-in pre-commit forcing-functions hook. REJECTED, on a verified mechanical ground.** `src/git-hooks/pre-commit-forcing-functions.sh` resolves `$ROOT/.devforge/constitute.json` and `$ROOT/.devforge/lib/constitute_helper`, and **exits 0 silently when either is absent** (lines 25–34). This repo's own root `.devforge/` contains a single configure file and neither of those paths (verified 2026-08-12), so the hook would no-op here. Independently: that hook is the **consumer-side** surface shipped into target projects — putting a maintainer privacy rule in it would ship this repo's problem to every consumer. Rejected on both grounds.
- **Option C — a standalone maintainer CLI.** Matches `scripts/verify-agent-reachability.py`, which additionally sets the honesty precedent this plan needs: that script states its coverage bound in its module docstring *and prints it in its own output* ("Does NOT cover type-2 forward-prose or type-3 finding-inertness"), so a passing run cannot be misread as full coverage. Worth copying verbatim in spirit.

**Recommendation: A + C together, in plan 41's exact three-file shape (D5).** The CLI gives an explicitly invocable check with a self-describing coverage bound; the pytest test makes it run without anyone remembering to. Neither alone is sufficient — the CLI alone depends on human discipline, which is the thing that demonstrably failed here.

**Honest coverage bound of the recommended guard — state this in the code, not just here:**
- **False negatives (what it structurally misses):** every name class — company, product, repository, component, prop, symbol, package prefix. None has a distinguishing shape. These are precisely the classes the first substitution pass targeted, so the guard does not cover the majority of what has already been found. Only the inventory covers them, and only for values a human listed.
- **False positives (the seeding cost):** measured on `tests/` 2026-08-12 with two first-cut shape probes — a ticket-ID-shaped pattern matched 11 files / 64 occurrences, and a 7–40-character hex pattern matched 27 files / 93 occurrences. **Nearly all are legitimate synthetic fixtures.** These numbers are *not* evidence of leak volume; they measure the one-time cost of seeding the synthetic allowlist, and they are what Phase 4 must price. Post-seeding the false-positive rate goes to zero by construction, and adding a new fixture SHA thereafter requires declaring it — which is the point.
- **The bound in one sentence: a shape-based check catches CLASSES, a list-based check catches INSTANCES, and they are not substitutes for each other.**

## Open questions (Phase 0)

- **OQ-1 — does the maintainer's own test-harness project name count as an identifier to scrub?** It appears in `src/` code comments, in generated documentation, and across many plan documents. It is the maintainer's own project, not the client's — but the instruction that prompted this work was categorical about real project names. Including it is the only path in this plan that touches shipped code; excluding it leaves `src/` untouched. **Recommendation: EXCLUDE.** It discloses nothing about a third party, and the entire justification for this work is third-party confidentiality. **Counter, stated fairly:** it is still a real, non-public project name; a categorical rule is easier to hold than a judgment call about whose name is whose; and a future contributor cannot infer the carve-out from the artifacts. **This is explicitly the maintainer's call** — the recommendation is not a decision, and this plan deliberately avoids writing that name anywhere so it remains correct under either answer.
- **OQ-2 — where does the synthetic-vocabulary mapping live?** Substitutions already applied must be **reused, not re-chosen**, or the same real identifier maps to two different fakes in two files — which is both a correctness bug in the fixtures and a partial de-anonymization hint. The mapping's left column (real values) cannot be committed. Candidate: the same out-of-repo inventory file as D3, carrying `real → class → synthetic → is-join-key` in one table, with only the `synthetic` column mirrored into the in-repo allowlist. Confirm the file's home and format at Phase 0; it is a prerequisite for Phase 2, not an implementation detail.
- **OQ-3 — does the fixture data need to be realistic at all?** Several of these values exist only to be stored and compared. Where a test does not depend on a value resembling real data, the strongest fix is a fixture that is **obviously synthetic by construction** — self-evidently fake to any reader, so the question "is this real?" never arises again. **Partly answered already by D7:** verified against file 2, some values *are* load-bearing, but what they carry is SHAPE (hex-ness, length, regex-triggering token order, repetition), never realism. Recommendation: obviously-synthetic-by-construction everywhere, shape-preserving where an assertion requires it.
- **OQ-4 — hard-fail or warn on day one?** Given the seeding cost measured above, a hard-fail guard blocks the suite until the allowlist is fully seeded. Recommendation: hard-fail, with allowlist seeding done *inside* Phase 4 so the suite is green when the phase closes. A warn-only guard is not recommended — a warning in a suite nobody reads warnings from is decoration.
- **OQ-5 — should the guard scan file PATHS as well as file CONTENTS?** A content grep does not see filenames. One repo-root document was observed on 2026-08-12 whose **filename itself embeds a ticket-ID-shaped token** — that particular file is plan-tier and is covered by the ratified deletion disposition, so it is out of this plan's scope, but it demonstrates the class. Recommendation: yes, scan paths — it is nearly free and closes a hole that content scanning cannot see by construction.
- **OQ-6 — does the guard cover plan documents written AFTER go-live?** **Read this together with the Non-goals, which it does not contradict.** The deletion disposition handles the *existing* set of plan documents; it does nothing about the *next* one written after go-live, and the exemption policy that produced this situation would still be in force for it. Scrubbing existing plan documents stays a non-goal; whether the guard's *scope* extends to future ones is a live and separate question. Recommendation: extend the guard to repo-root `*-PLAN.md` at whatever point the deletion lands, so the cleaned state is defended rather than merely reached.

## Dependencies

- **The in-flight follow-up pass** (two SHA-shaped strings + the package prefix) must land before Phase 3 can verify anything. Phase 3 is a verification of that pass, not a re-run of it.
- **The out-of-repo inventory (D3 / OQ-2)** is a hard prerequisite for Phases 1, 2 and 3. Without it, those phases can only verify substitutions against themselves — the original failure.
- **Nothing in the forge pipeline depends on this plan**, and this plan blocks no other work. It is independent of the go-live deletion except at OQ-6.

## Non-goals

- **Scrubbing plan documents or `done-plans/`.** Deletion at v2 go-live is the ratified disposition. Do not scrub, rewrite, or partially clean them — partial work there consumes effort and changes nothing, since deletion supersedes it.
- **Any git-history rewrite.** Not proposed, not designed, not scoped. The limitation is recorded above and routed to a separate decision. A history rewrite on a public repository has consequences for every clone and fork and is not a side effect of a fixture cleanup.
- **Any change to `src/`, `scripts/`, or `docs/`** — unless OQ-1 resolves against the recommendation, which is the sole path that reaches `src/`. (Phase 4 adds *new* files under `scripts/` and `tests/`; it modifies no existing shipped file.)
- **Rewriting the repo's plan-exemption policy document.** This file declines to rely on the exemption; changing the policy is a maintainer decision that OQ-6 surfaces but does not settle.
- **Any change to what the framework ships to consumers.** The measured inventory shows `src/` clean; consumers are not exposed by this and must not be affected by the fix.

## Phases

### Phase 0 — Ratify (maintainer gate)
Maintainer confirms D1–D8 and answers OQ-1 through OQ-6. **No file is edited before ratification** — in particular, OQ-1 determines whether the blast radius includes `src/`, and OQ-2 determines whether Phase 2 can start at all.
**Verify:** a user reply recording each pick. Absence of a reply is not tacit approval.

### Phase 1 — Build the identifier inventory (must precede all substitution — D2)
Produce the out-of-repo inventory per D3/OQ-2: one row per real client identifier, carrying its class, its approved synthetic replacement, and its join-key flag (D8). Populate it by **exhaustive `ast` literal enumeration** over all three test files plus a line-based scan of the non-`.py` fixture files under `tests/lib/fixtures/` (9 `.md`/`.json` files exist there as of 2026-08-12 and `ast` does not read them), classifying every extracted literal as `synthetic-safe`, `client-derived`, or `unknown`. **`unknown` is resolved, never defaulted to safe** — defaulting to safe reproduces the original failure with extra steps.
**Verify:** zero literals remain in the `unknown` state — an undispositioned literal is visibly a hole in the artifact, which is the property this phase exists to have. Every `client-derived` row carries a synthetic replacement and a join-key determination. The inventory file resides outside the repository working tree; `git status` shows no new file.

### Phase 2 — File 2: the research handoff-schema test (python-engineer → python-reviewer)
Substitute every `client-derived` literal in file 2 using the Phase-1 inventory's approved replacements — reused, never re-chosen (OQ-2). Apply D7: preserve each value's assertion-relevant shape (character class, length, token ordering, repetition) and discard its meaning. Confirmed present in this file as of 2026-08-12, by class: a ticket-ID-shaped token embedded in a fixture commit-subject string, two commit-SHA-shaped hex strings (one a prefix of the other), a camelCase value identifier used as fixture data, and boolean-prop / function identifiers used in fixture prose and in assertion strings.
**Verify:** the file's full test class set passes unchanged — same test count, no test weakened or deleted to accommodate a substitution. Re-run the Phase-1 enumeration against the edited file: zero `client-derived` rows remain. Schema-level assertions that depend on hex-ness, minimum length, or regex triggering still exercise the branch they were written for (D7) — confirm by reading each changed assertion, not by observing that the suite is green.

### Phase 3 — Verify files 1 and 3 against the inventory (not against the substitution table)
Gated on the in-flight pass having landed. Re-run the Phase-1 enumeration over files 1 and 3 and check each extracted literal against the **inventory**, not against the list of things that were replaced. Explicitly re-check join keys (D8).
**Verify:** zero `client-derived` and zero `unknown` literals in either file. Zero surviving join keys. If any join key survives, the file is reported **NOT DONE** — not "clean with a caveat". State in the phase's closing note which classes the check covered and which it structurally could not (the name classes), so the result is not over-read.

### Phase 4 — Recurrence guard (python-engineer → python-reviewer)
Per D5, in plan 41's three-file shape: `scripts/lib/` scanner module + `scripts/` CLI + a `tests/lib/` test that runs the scan against the live tree so it executes on every `pytest` invocation. Behavior per D4 (loud skip, never silent pass), D6 (hard-fail on undeclared shape-bearing literals; advisory-only on name-shaped literals), and OQ-5 (scan paths as well as contents, if ratified). Seed the in-repo synthetic allowlist in this same phase so the suite closes green (OQ-4). Copy the honesty precedent from the existing reachability CLI: the coverage bound goes in the module docstring **and** is printed in the check's own output, so a passing run cannot be misread as full coverage.
**Verify:** the check fails on a deliberately introduced shape-bearing literal that is absent from the allowlist — this is the load-bearing test, because it is the one that proves the guard catches something nobody listed. The check announces SKIPPED (not PASS) when the inventory path is unset. Full suite green with the allowlist seeded. The printed output states the false-negative bound in words.

### Phase 5 — Docs reconcile
`CHANGELOG.md`; a repo-root `CLAUDE.md` active-work entry; a "Where to find what" row for the new guard alongside the existing agent-reachability row. Record the ratified deletion disposition **and its git-history limitation** wherever the disposition is stated, so no future session reads "deleted" as "unretrievable".
**Verify:** cross-ref sweep for the new module, CLI, and allowlist names returns no dangling reference. The history limitation appears everywhere the disposition does — a session that reads only one of the two must not come away with the wrong belief.

### Phase 6 — Final sweep and honest closing statement
Re-run the Phase-1 enumeration across all of `tests/`, not only the three named files. Write the closing statement in the terms the coverage bound requires: what was enumerated, what was dispositioned, what class of identifier the process structurally cannot detect, and that the inventory's completeness is asserted rather than proven.
**Verify:** the closing statement contains no claim of the form "the repository is clean" — the defensible claim is narrower, and stating the narrow one is the entire point of this plan.

## When resuming work

1. Read this plan in full, and re-read the lesson section before touching any file — the ordering rule in D2 is the thing most likely to be lost.
2. **Re-measure the inventory table.** It is a 2026-08-12 snapshot. Treat the numbers as stale.
3. Confirm whether the in-flight follow-up pass landed; Phase 3 is blocked on it and Phase 2 is not.
4. Re-verify the anchors this plan cites before relying on them (this repo has documented anchor rot): `scripts/lib/agent_reachability.py`, `scripts/verify-agent-reachability.py`, `tests/lib/test_agent_reachability.py`, `src/git-hooks/pre-commit-forcing-functions.sh` lines 25–34, and the absence of any repo-root pytest/CI/Makefile config.
5. Locate the out-of-repo inventory before starting Phase 1 or 2. If it does not exist, Phase 1 creates it; if it exists, **reuse its mappings rather than choosing new ones** (OQ-2).
6. Start at Phase 0. Do not skip to substitution — a substitution performed before the inventory exists can only be verified against itself, which is the documented failure this plan is built to avoid.
