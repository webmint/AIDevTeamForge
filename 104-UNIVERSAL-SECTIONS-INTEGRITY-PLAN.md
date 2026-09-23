# 104 — Universal Sections Integrity Plan

**Created**: 2026-09-20
**Status**: **Phase 0 NOT STARTED.** Nothing here is ratified, nothing here is built, and **no build phase may start** until `## Phase 0 close record` carries an outcome for every one of D1–D7 and OQ-1–OQ-3. Every "RECOMMEND" below is a drafting-time proposal, not a decision.

⚠ **Evidence class, to be repeated in every summary of this plan: ONE observed thing only — a user hit F1's label confusion in a real run and asked whether it was a bug. F2, F3 and F4 were found by READING. Nothing was measured, no consumer incident stands behind them, and a clean consumer run at the end of this plan would show the chain behaves on planted fixtures, never that any of these gaps cost anything.**

**The one sentence that governs everything here:** the chain that puts universal sub-sections into a consumer's `constitution.md` is unclosed at every link — the spec names wrong numbers, nothing supplies the canonical body text, the drift detector cannot return green, and the tests hide it.

---

## Origin & evidence

- **The one observed thing (F1).** A user reading a real `/devforge:constitute` run met the string *"Section 3.5"* in the user-facing echo, compared it to the constitution's own §3.5, and asked whether it was a bug. It is a label collision, not a mechanism defect — and it is the only part of this plan anyone has ever reported.
- **F2, F3 and F4 were found by reading**, in the session that followed that question. Each is recorded below with the `file:line` it was checked at on 2026-09-20. **None was observed failing on a consumer, and no count, rate or cost was measured.**
- **F4 is separately recorded in this project's memory** as `verify-universal-defaults-broken` (memory file present 2026-09-20). That record and this plan are the only places it exists.
- **The 2026-09-20 reverted session.** See `## Context for next session` — Facts 1 and 2 were fixed in the tree that day and every edit was then reverted, on the maintainer's observation that the work should have been a plan rather than a series of audit fixes. **Nothing from it survives in the tree**, and this plan is written as if none of it happened, because in the tree none of it did.

### Verified structure (2026-09-20)

Every fact below was checked against the tree on 2026-09-20. ⚠ **Line digits drift — grep the quoted text, never the digits.**

#### F1 — the "Section 3.5" label collision

- **Seven sites in `src/commands/constitute/main.md`** (grep `Section 3.5`): the echo-template heading `### Section 3.5 echo template (Forcing Functions — config block, not a constitution.md sub-section)` (`:235`), the template body (`:237`), **the USER-FACING echo line** *"Here's what /devforge:constitute proposes for Section 3.5 — Forcing Functions [config-block]:"* (`:255`), the setter-plan bullet (`:329`), the setter-call block (`:406`), a comment in that block (`:433`), and one more at `:563`.
- **One site in `src/CLAUDE.md`** (`:129`, the `#### /devforge:constitute` catalog entry): *"Its Section 3.5 forcing-functions config-capture offers the `design_token_provenance` rule …"*. This file is emitted into every consumer project.
- **The real §3.5** is `src/constitution.md:62` — `### 3.5 Universal Code Quality [universal]`.
- **The block is structurally not a numbered sub-section.** It targets the top-level `forcing_functions` key in `.devforge/constitute.json`, and `_cmds_render.py`'s `section_bucket_keys` walk (`:108-113`) iterates only `["architecture_rules", "code_quality_standards", "domain_rules", "workflow_rules"]`. A `forcing_functions` entry can therefore never render as a `3.x` sub-section.
- **The spec already disambiguates — in model-facing prose only.** `:235` (*"config block, not a constitution.md sub-section"*), `:237` and `:329` (*"Does NOT issue `add-section` — `forcing_functions` is a top-level config block, not a numbered constitution.md sub-section."*) all say it. **`:255` is the line the user reads, and it says none of it.**

#### F2 — the spec's sub-section numbering contradicts the canon

**Canonical `src/constitution.md`** (grep the headings):

| Number | Canonical heading | Tag |
|---|---|---|
| 3.1 | Type Safety | `[project-specific]` |
| 3.2 | Error Handling | `[project-specific]` |
| 3.3 | Naming Conventions | `[project-specific]` |
| 3.4 | Testing Requirements | `[project-specific]` |
| 3.5 | Universal Code Quality | `[universal]` |
| 3.6 | Design Principles | `[universal]` |
| 3.7 | Check Before You Build | `[universal]` |
| 3.8 | Design Fidelity | `[universal]` |
| 6.1 | Minimal Changes | `[universal]` |
| 6.2 | Semantic Understanding | `[universal]` |
| 6.3 | Read-First Principle | `[universal]` |
| 6.4 | Documentation | `[universal]` |
| 6.5 | Deprecation Handling | `[project-specific]` |
| 6.6 | Project-Specific Workflow | `[project-specific]` |

**What the spec tells the model to compose.**

- `constitute/main.md:103`: *"Compose 4-7 sub-sections (e.g., 3.1 Type Safety, 3.2 Error Handling, 3.3 Naming Conventions, 3.4 Testing Requirements, 3.5 Documentation, 3.6 Function Length, 3.7 Check Before You Build)"*. **3.8 is never mentioned.**
- `constitute/main.md:134`: *"Compose 4-6 sub-sections … (e.g., 6.1 Minimal Changes, 6.2 Read Before Write, 6.3 Search Before Building, 6.4 One Task At A Time, 6.5 Pre-flight Check, 6.6 Project-Specific Workflow)"*.
- `references/section-shapes.md`, Section 3: *"**Shape**: 4-7 sub-sections"* and *"**Sub-section count expectation**: 6 typical. Common sub-sections: Type Safety, Error Handling, Naming Conventions, Testing Requirements, Documentation, Function Length / Complexity."*
- The same file, Section 6: *"**Shape**: 4-6 sub-sections"* and *"6 typical. Common sub-sections: Minimal Changes, Read Before Write, Search Before Building, One Task At A Time, Pre-flight Check, Project-Specific Workflow."*
- The same file, Section 3 opening prose: *"`universal` for stack-agnostic dimensions like "Function Length""* — offering a dimension the canon does not have.
- The same file: *"**CBM-first protocol rule (Section 3 Documentation sub-section)**"* — anchoring a shipped `[enforced]` rule to a sub-section name that exists nowhere in Section 3 of the canon.

**Six of the eight universal numbers are wrong or absent.** Against the canon: 3.7 Check Before You Build and 6.1 Minimal Changes match; 3.5, 3.6, 6.2, 6.3 and 6.4 carry a different heading than the canonical one at that number; 3.8 is absent from the list entirely.

**§4.1–§4.3 are unaffected.** Their numbers are fixed in the canonical file's own headings (`src/constitution.md` — `### 4.1`, `### 4.2`, `### 4.3`); `add-pattern-rule` appends to a named `patterns_and_antipatterns` bucket and the state records that bucket name, never a number. `_PATTERNS_BUCKET_TO_SECTION` (`_schema.py:303-307`) is on neither the setter path nor the render path — its only use site is the **comparison** side, `_universal.py:276`, where the consumer-side extractor turns a bucket name into a `§`-number key. Either way, no number here is ever composed by the model.

**The arithmetic defect.** `main.md:103` says *"Compose 4-7 sub-sections"* while the canon holds **8**. `section-shapes.md` says *"Shape: 4-7"* and *"6 typical"*. **A range that cannot hold the canon is structurally why 3.8 fell off the list.** (Section 6's *"4-6"* does hold the canonical 6; only Section 3's range is short.)

**The consequence.** `cmd_render` rebuilds `constitution.md` entirely from state — `main.md:15` calls it a *"render artifact rebuilt from `.devforge/constitute.json` on every `render` call"*, `:512` says render *"walks the locked schema, manually concatenates `constitution.md` per section, and atomically writes the result"*, and `:518` says *"The LLM does NOT edit `<install_root>/constitution.md` directly via the Write or Edit tool at any point. The helper's `render` is the only writer."* So a sub-section composed at a wrong number means **the canonical universal content is simply ABSENT from that consumer's constitution** — not misplaced, absent.

#### F3 — nothing supplies the universal body text

- **The four inputs `/devforge:constitute` reads** are `INIT_JSON` (`main.md:49`), `CONFIGURE_JSON` (`:55`), `DOCS_JSON` (`:72`) and `GLOSSARY_JSON` (`:78`). **None carries canonical constitution prose** — they carry init fields, configure answers, parsed `docs/` content and glossary term records.
- **`.devforge/template/` holds only `.claude/agents/` + `CLAUDE.md`** (`install.sh:432-434`: `mkdir -p "$TARGET_DIR/.devforge/template/.claude/agents"`, then two copies and nothing else).
- **`install.sh:365` does copy `src/constitution.md` to the consumer's project root — and that copy is not a usable source.** Three reasons, each checked: it is presence-guarded (`install.sh:364` — `if [ ! -f "$TARGET_DIR/constitution.md" ]`, else *"existing constitution.md detected — leaving as-is"*); **no instruction anywhere tells the model to read it** (`main.md:15` names that path as an OUTPUT artifact, never an input); and on any re-run that path holds the previously **rendered** constitution, not the template.
- **There is no seeding verb.** `constitute_helper` registers **27** subcommands (27 `add_parser(` calls in `_constitute/_cli.py`): `reset`, `read-init`, `read-configure`, `read-docs`, `read-glossary`, `set-project-name`, `set-mode`, `set-dates`, `set-project-identity`, `add-section`, `add-rule`, `add-table`, `add-code-example`, `add-pattern-rule`, `set-scaffolding-guide`, `render`, `verify`, `summary`, `validate`, `verify-magic-enum`, `verify-cross-layer-imports`, `verify-any-leak`, `verify-design-tokens`, `set-forcing-functions`, `list-forcing-functions`, `forge-internal:verify-universal-defaults`, `forge-internal:verify-forcing-function-keys`. **None of them seeds universal sections.**
- **The text is static and reproducible in principle.** A `{{` grep over `src/constitution.md` returns hits only in the header block and inside §3.2 and §3.4 (`{{ERROR_HANDLING}}`, `{{TESTING}}`). **§3.5–§3.8 and §6.1–§6.4 contain no placeholder at all.**
- **Today the model reproduces that text from memory, or not at all.**

#### F4 — `verify-universal-defaults` cannot return green on a real install

The two comparison sides build the per-rule key from different things.

- **Canonical side, `_universal.py:84`** (the default branch of `_parse_universal_blocks`): `rules = [{"tag_or_label": heading, "body": body_text}]` — **the key is the SECTION HEADING**, e.g. `"Universal Code Quality"`. (§3.6 takes `_split_design_principles` and §4.1–§4.3 take `_split_bullet_rules`; both produce bold sub-labels as keys, e.g. `"Single Responsibility"`.)
- **Consumer side, `_universal.py:270`**: `{"tag_or_label": r.get("tag", ""), "body": r.get("text", "")}` — **the key is `rule.tag`**, a member of the `rule_tag` enum `{extracted, enforced, universal, project-specific}` (`_schema.py:268`). The patterns-bucket branch at `:281` does the same.
- **`_cmds_quality.py:184-212`** builds both dicts keyed on `tag_or_label` and reports `MISSING` for every canonical label absent from the consumer keys, then `DRIFT` on a body mismatch. **`heading` is carried in the return shape by `_universal.py:86` and never compared — the string `heading` does not appear in `_cmds_quality.py` at all.**
- **No enum value equals a heading string, so every universal section reports MISSING even for a perfectly composed consumer.** §3.6 and §4.1–§4.3 mismatch for the same reason with different canonical keys.

**Two filters compound with F2, checked at `_universal.py:259-265`.** The consumer side skips any section whose `tag != "universal"` and any section whose `number` is not in `_UNIVERSAL_SECTIONS` (`_schema.py:296-300` — a closed eleven-entry tuple: §3.5–§3.8, §4.1–§4.3, §6.1–§6.4). **So a sub-section composed at a wrong number (F2) never enters the comparison either** — the same `MISSING` line, from a second independent cause. Fixing one cause alone does not make the detector green.

**The tests do not catch this, and say why in their own docstring** — `tests/lib/test_constitute_helper.py`, `class TestForgeInternalVerifyUniversalDefaults`: *"All 3 tests use hand-authored constitute.json fixtures because the ``add-rule`` setter constrains ``--tag`` to enum values, so principle names like "Single Responsibility" cannot be stored via the CLI."* The shared builder `_build_in_sync_constitute_json` writes `{"tag": r["tag_or_label"], "text": r["body"]}` for all eleven sections — **the canonical heading into the `tag` field, a state the real CLI rejects** (`add-rule` validates `--tag` against the enum; `test_invalid_tag_exits_2`).

⚠ **This violates the repo's own real-producer principle, and it is recorded in that class's docstring as a fixture *strategy*, not as a defect.**

#### F5 — what F4 means for anything that ever ran the detector

- **The detector is not maintainer-only in practice.** `scripts/constitution-drift-check.sh:54` invokes `forge-internal:verify-universal-defaults`, and that function is sourced and called from **`install.sh:371`** (the brownfield *"leaving as-is"* branch) and **`update.sh:247`** (every update of a constituted consumer). It is **WARN-only and fail-soft** — on exit 2 it prints *"⚠ Constitution out of date — framework law has changed since this project was constituted:"* with a per-section rule count, and returns 0.
- **So under F4 every constituted consumer sees that warning on every update, naming every universal section, regardless of whether anything drifted.**
- **There are five `verify-universal-defaults` tests, not three.** Beyond the class above, `test_verify_universal_defaults_detects_missing_38` builds a bare `default_state()` (nothing populated) and asserts `MISSING §3.8` — which passes trivially — and `test_verify_universal_defaults_passes_with_38_in_sync` calls the **same** hand-authored `_build_in_sync_constitute_json`.
- **The real-producer path exists for the extractor and never reaches the comparator.** `TestExtractUniversalRulesFromState` opens with *"Real-producer principle: fixture states are built via the actual constitute_helper CLI (reset + add-section + add-rule + add-pattern-rule) rather than hand-authored JSON"*, and `test_happy_path_real_producer` asserts `result["§3.5"]["heading"] == "Universal Code Quality"` — **it reads the `heading` key, which is the one the comparator ignores.** No test feeds `_build_real_constitute_state`'s output to `verify-universal-defaults`.

⚠ **The consequence this plan must state and must NOT conclude.** The "designed consumer drift" that plans 86, 89 and 99 each tell consumers to expect may be an ARTIFACT of F4 rather than real drift. **This plan does not get to decide that** — OQ-2 owns it, and it is established by a run, not by reading. A fourth candidate exists and is recorded here so it is not missed: `44-CONSTITUTION-DRIFT-WIRING-PLAN.md` reports *"~30 MISSING universal rules across §3.5/§3.6/§3.7/§3.8/§4/§6"* and *"validated on testForge20 with exit 2 + 29 MISSING findings"* — a count that F4 predicts for an in-sync install just as well as for a drifted one, so **that observation cannot distinguish the two and is not evidence either way.**

#### F6 — the override grammar embeds the tag

`constitute/main.md:224-228` — the generic per-section echo footer offers four overrides, two of which carry a tag token:

```
  - 'add rule <number>: [<tag>] <text>'             — append a rule to sub-section <number>
  - 'drop rule <number>:<index>'                    — remove rule at 1-based index from sub-section <number>
  - 'replace rule <number>:<index>: [<tag>] <text>' — replace rule at 1-based index
  - 'drop section <number>'                         — drop the entire sub-section
```

This grammar is offered against every section, universal ones included. It is D5's blast radius on the user-facing side and D6's subject on the policy side.

#### F7 — `validate`'s rule-tag dimension

`_validate_metrics.py` Dim 4 is `rule_tag` — *"every rule tag in closed enum"* — with **weight 0.20** and **pass threshold 1.0** (*"rule_tag is mechanical (any invalid tag is …)"*), checked against `ENUM_FIELDS["rule_tag"]`. **A rule carrying any label outside the enum fails Dim 4 outright and costs up to 0.20 of the composite**, against the Phase 6.2 ship/cancel/fix human gate that fires below 0.95. This is the mechanical cost of D5's permissive arm, and it is the number to argue with.

#### The checkout

**F8 — Concurrency.** Other sessions build in this checkout, and **plan numbers are allocated with no coordination between them**: each session takes the next free number from what it can see, and what it can see goes stale while it drafts. This is neither hypothetical nor rare — **this file's own number was taken and re-taken more than once inside the single session that produced it**, and the neighbouring sessions' files moved repeatedly over the same stretch, at one point leaving the same plan title sitting at two numbers at once, a rename caught mid-flight. A rename moves a file and never the sentences inside it, so **a document that cites another plan by number alone is citing a value that drifts** — where the citation matters, name the work, not the digits. Before touching any ledger, re-read `git status`, read the ledger live, and **commit by explicit path, never `git add -A`.** Do not touch a plan file this session did not create, for any reason: ownership is established from `git status` and from which sessions are active, never from a plan's number.

---

## The chain, link by link

| Link | What should happen | What happens today | Fact |
|---|---|---|---|
| 1. The spec names the sub-sections | The model is told the canonical numbers and headings | Six of eight universal numbers are wrong or absent; the range cannot hold the canon | F2 |
| 2. Something supplies the body text | The canonical prose reaches the run | No input carries it; the root copy is presence-guarded, uninstructed and overwritten by render | F3 |
| 3. The state records them | `add-rule` stores a rule with an identity | `--tag` is the only identity and it is a four-value enum | F4, F6 |
| 4. The detector compares | An in-sync consumer returns exit 0 | Heading vs enum value — every universal section reports MISSING | F4 |
| 5. The tests hold the line | A real-producer in-sync fixture proves exit 0 | All five verify tests use hand-authored or empty state; the real-producer fixture never reaches the comparator | F4, F5 |

**Link 1 alone is a trap.** Fixing F2 without F3 changes the failure mode rather than removing it: with correct numbers and no body-text source, the model produces the canonical heading at the canonical number and **invents** the body. That is quieter than today's absence, not louder — and link 4 would then report `DRIFT` instead of `MISSING`, which reads like a smaller problem. **This is the whole argument for treating delivery as inseparable from numbering.**

---

## Decisions to ratify

**Nothing below is ratified.** Each item states the decision, the options, a recommendation and the strongest counter-argument, **recorded rather than answered away**. Proposed emitted wording is **substance, not final text**: the builder may reword, but every element named must survive. **No emitted sentence may name plan vocabulary ("D5", "plan NN", "Phase 0", "F4").**

### D1 — Scope: does this plan include the label fix, or only the mechanism?

F1 (the "Section 3.5" label collision) and F2–F4 (the universal-sections chain) are two problems that share a number and nothing else. F1 is a text-honesty fix on a block that works correctly; F2–F4 are a broken mechanism.

- **(a) Both, in one plan.** One ratification, one docs sweep, one consumer run.
- **(b) Mechanism only**; F1 goes to its own plan or a standalone fix.

- **RECOMMEND (a)**, with this recorded: **the label fix is independently shippable.** It depends on no other decision here, blocks nothing, and is not blocked by anything — its phase carries an explicit "may ship alone" note so a later session is never forced to drag the mechanism work along to land it. It rides here because it is the one part of this subject a user has actually met, and splitting it would leave the only observed item ownerless.

**Counter-argument, recorded:** bundling an observed one-line-class fix with an unobserved four-fact mechanism rebuild means the observed fix waits for the unobserved one to ratify. If Phase 0 stalls, the user-visible confusion stays in the tree — which is exactly why the "may ship alone" note is part of the recommendation and not a nicety.

### D2 — Source of canonical text

Nothing supplies §3.5–§3.8 and §6.1–§6.4 body text to a `/devforge:constitute` run (F3). Something must.

- **(a) A snapshot at `.devforge/template/constitution.md`** — one added line in `install.sh`'s existing snapshot block (`:432-434`). ⚠ **That line must copy from `$TEMPLATE_DIR/src/constitution.md` directly** — `install.sh:365`'s pattern, **not** the block's own two lines' pattern: `:433-434` both copy from `$TARGET_DIR`, and `$TARGET_DIR/constitution.md` holds the shipped template only on the branch where `:365` ran. On a brownfield reinstall the presence guard at `:364` takes its `else` branch (`:366-372` — OQ-3's), `:365` never runs, and that path holds whatever the consumer already had, most likely a previously **rendered** constitution. **Sourcing from `$TARGET_DIR` would break this option's own guarantee on exactly the installs where it matters.** Sourced from `$TEMPLATE_DIR`, the run reads a path that is by construction the shipped template and never a rendered artifact, whichever branch the guard took.
- **(b) Inline the canonical prose into the spec** — the text lives in `constitute/main.md` or a reference file, and the model composes from what it reads.
- **(c) Another route** — a helper verb that emits the canonical blocks on stdout (which collapses into D3), or reading `src/constitution.md` from the installed template directory directly.

- **RECOMMEND (a)**, **conditionally and subject to re-derivation after D5.** It adds one line to a block that already exists and already solves exactly this problem for agents and `CLAUDE.md`; it puts the text where an update ships it; and it keeps the canonical prose single-sourced in `src/constitution.md`.
- ⚠ **Sequencing note, load-bearing: D2 is decided AFTER D5.** If D5 gives a rule an identity separate from its tag, the snapshot's required shape changes — a flat markdown copy may no longer be enough, and a structured emission (the (c) family) may become the cheaper carrier. **A ratifier who takes D2 before D5 has decided the carrier before knowing what it must carry.**

**Counter-argument, recorded:** (b) is the only option that needs no install-time change at all, and inlining reads as the simplest thing. It is not: `verify-universal-defaults` compares body text byte-for-byte after normalization, so inlined prose becomes **byte-critical duplication** — two copies of the same paragraphs that must never diverge, with the detector turning any divergence into a `DRIFT` finding on every consumer. That is the drift class this plan exists to close, reintroduced at a new site. Recorded and not answered away: (a) still leaves two copies on disk in a consumer (the snapshot and the render), but only one is ever read as a source.

### D3 — Who seeds the universal sections

Given a text source (D2), something must put those sections into `.devforge/constitute.json`.

- **(a) A new `seed-universal` verb** — the helper reads the canonical source and writes all eleven sections itself. Helper-owns-shape: the numbers, headings, tags and rule identities are the helper's, and the model composes nothing.
- **(b) Extend `reset`** — a freshly reset state already carries the universal sections. One fewer verb; every `reset` call in every test changes shape.
- **(c) The model follows an instruction** — the spec tells it to read the source and issue `add-section` / `add-rule` per universal sub-section.

- **RECOMMEND (a)**, **conditional on D5** — it becomes largely mechanical once D5 settles what a rule's identity is.
  - (c) is the option this plan exists to retire: it is what happens today, minus the text source, and it puts eleven exactly-specified sections back in the hands of the composer. Helper-owns-shape says the helper owns structure and the LLM composes values; canonical universal text has no values to compose.
  - (b) changes the meaning of `reset` from "empty state" to "state with content", which every existing test and every re-run assumes.

**Counter-argument, recorded:** (a) adds a 28th verb to a helper that already has 27, and the framework has a standing preference for extending one binary over adding another composer. Accepted as a cost, not refuted: the alternative that avoids the verb is (b), whose price is redefining `reset`.

### D4 — What keys a rule during comparison

`tag_or_label` currently means two different things on the two sides (F4): a heading (or bold sub-label) on the canonical side, an enum tag on the consumer side. The comparator dictionaries are built from it.

- **(a) Compare on a new identity field** that both sides populate with the same string (depends on D5 giving a rule such a field).
- **(b) Compare on the section `heading`**, which `_universal.py` already carries in the return shape and `_cmds_quality.py` already ignores — comparing whole-section bodies rather than per-rule ones for the default branch.
- **(c) Compare positionally** — rule *i* against rule *i* within a section.
- **(d) Keep `tag_or_label` and make the consumer side emit the same thing the canonical side does** (which collapses into D5).

- **RECOMMEND (a)**, **conditional on D5** — once a rule carries an identity separate from its tag, the comparator keys on it and the two sides mean the same thing by construction.
- **Recorded about (c):** positional comparison is the only option that needs neither a schema change nor a new field, and it is the one that fails silently — a consumer who legitimately appends one project rule to a universal section shifts every later index and the detector reports drift on rules nobody touched.
- **Recorded about (b):** it is strictly cheaper than (a) and strictly weaker. It would make §3.5, §3.7, §3.8 and §6.1–§6.4 comparable today with zero schema change, and it would leave §3.6 and §4.1–§4.3 — the sections whose canonical keys are bold sub-labels — exactly as broken as they are now.

**Counter-argument, recorded:** (a) is the most invasive option in a plan whose cheapest correct option is (b), and it is recommended partly because there are no production installs to protect (see `## Honest bounds`). If that ever stops being true, (b) becomes the proportionate answer for the sections it covers, and §3.6 / §4.x stay uncovered — which is a real, statable partial fix, not a failure.

### D5 — Does `add-rule` accept a label outside the `rule_tag` enum?

⚠ **This decision governs the rest. Once it is settled whether a rule carries an identity separate from its tag, D3 and D4 become largely mechanical.** Decide it first.

- **(a) Yes — a rule gains an identity field** (a label / name) distinct from `--tag`, which stays the four-value enum it is. The canonical side's heading or bold sub-label lands there; the consumer side emits it; the comparator keys on it (D4(a)).
- **(b) No — the enum stays the only identity**, and the comparison is repaired some other way (D4(b) or (c)).

- **RECOMMEND (a).**
- **Blast radius, stated so it is argued with rather than discovered:** the `rule` schema propagates to
  - `add-rule`'s CLI surface and its `--tag` validation,
  - `validate`'s Dim 4 `rule_tag` — **weight 0.20, pass threshold 1.0** (F7), so a label smuggled into `tag` costs up to 0.20 of the composite against a 0.95 human gate,
  - `render` (whether a label appears in the rendered constitution, and how),
  - **both** comparison sides in `_universal.py`,
  - the override grammar's `[<tag>]` token at `constitute/main.md:224-228` (F6), which is user-facing,
  - and the tests, including every fixture that constructs a rule.

**Counter-argument, recorded:** (b) is a real position and the cheapest one. The enum exists because a rule's tag is a *classification* — where the rule came from and whether it is universal — and a name is a different kind of thing that the schema deliberately did not carry. Adding one widens a locked schema across seven surfaces to serve a comparator that (b) could repair in one file. The case for (a) is that F4's root cause **is** the absence of an identity: the comparator did not invent the mismatch, it inherited a schema in which a rule has no name to compare.

### D6 — Fate of user overrides over universal rules

Today the per-section echo offers `add rule` / `drop rule` / `replace rule` / `drop section` against every section, universal ones included (F6). Once universal sections are seeded by the helper with canonical text (D2, D3), a user override against one of them is a deliberate divergence — and the detector will report it as `DRIFT` on the next update, forever.

- **(a) Overrides stay available against universal sections**, and the resulting drift finding is accepted and named as such in the echo.
- **(b) The override grammar is withheld for universal sections** — the echo offers them for project-specific sections only, and a universal section is presented as law.
- **(c) Overrides stay available, and an overridden universal rule is recorded** so the detector can tell a deliberate override from stale text.

- **RECOMMEND (a)** — with the echo saying plainly that an override of a universal rule will be reported as drift on every update until it is reverted.
- **Why not (b):** it removes a capability a user has today, on a plan with no evidence anyone misused it, and it makes `drop section` mean different things in different sections of the same echo.
- **Why not (c):** it is the correct answer and the expensive one — a per-rule override record is a second schema change on top of D5's, with its own comparison semantics. **Recorded as the named strengthening arm, with an observable trigger: a user who reverts an intentional override because the drift warning kept naming it.**

**Counter-argument, recorded:** (a) knowingly ships a warning that cannot be silenced without undoing the user's own decision, and a warning a user learns to ignore is worse than no warning — it trains them past the real ones too. That is accepted here, not refuted, because (c)'s cost is a second schema change and (b)'s cost is removing a capability.

### D7 — Section 3 numbering: a fixed 8, or a range?

`main.md:103` says *"Compose 4-7"* and `section-shapes.md` says *"Shape: 4-7"* / *"6 typical"*, while the canon holds 8 (F2).

- **(a) A fixed 8** — 3.1–3.4 project-specific (composed), 3.5–3.8 **reserved** for the universal set (seeded, never composed). Section 3 always renders eight sub-sections.
- **(b) A corrected range** — e.g. "5-8", with 3.5–3.8 reserved and 3.1–3.4 composed to taste.

- **RECOMMEND (a).** The universal four are not a matter of degree: they are either all present or the constitution is missing framework law. A range invites the model to stop early, which is exactly how 3.8 went missing. A fixed count is mechanically checkable — the number of `code_quality_standards` entries with `tag == "universal"` is 4 or it is not.
- **Record explicitly: "4-7" cannot hold the canonical 8**, whichever option is ratified. Any arm that leaves that string in the tree has not fixed F2.
- **The project-specific half stays a range.** 3.1–3.4 are examples, not a mandate; a project with no meaningful naming conventions should not be told to invent a sub-section.

**Counter-argument, recorded:** (a) hard-codes a count into prose that a future constitution amendment can falsify — add §3.9 and every "fixed 8" sentence is wrong in the same release. That is a real maintenance edge. It is preferred anyway because the failure mode is loud (a stated count that no longer matches is visible) while the range's failure mode was silent (a section quietly absent for as long as anyone has been running this).

### OQ-1 — Are the three (five) tests rewritten onto the real-producer principle?

The repo's own rule is that tests use input shapes matching production, round-tripped via the real producer. Five `verify-universal-defaults` tests do not (F4, F5).

- **RECOMMEND yes**, in this plan, as its own phase: a real-producer in-sync fixture built through the CLI (`reset` + the seeding route D3 ratifies) fed to the comparator, asserting **exit 0**. **That single test is the only thing that would have caught F4, and it is the only thing that will catch its return.**
- **Alternative:** keep the hand-authored fixtures and add one real-producer test beside them. Cheaper, and leaves four tests that pass on a state the CLI rejects.
- ⚠ **Note for whoever ratifies:** this test cannot be written before D5 and D3 are built. A real-producer in-sync fixture requires a route by which canonical text and identities enter the state through the real CLI. That is a phase ordering constraint, not an argument against.

### OQ-2 — Are the plans 86 / 89 / 99 "designed drift" claims artifacts?

Plans 86, 89 and 99 each tell consumers to expect a `verify-universal-defaults` DRIFT/MISSING finding as designed consequence of a constitution amendment. **Under F4 those findings would appear whether or not anything drifted.**

- **RECOMMEND: establish it by a run, not by reading, and record the result in this plan's own build record.** The run is: a real-producer in-sync consumer state (OQ-1's fixture) against the current canonical file, **before** the comparison fix and **after** it. Before-fix exit 2 with every universal section MISSING, after-fix exit 0, is the finding.
- **If established true:** the three ledger entries get **dated amendments**, never rewrites — the claim stays on the record, with a dated note saying the finding it predicted was not distinguishable from an artifact of the comparator. `44-CONSTITUTION-DRIFT-WIRING-PLAN.md`'s *"~30 MISSING"* / *"29 MISSING findings"* records are a **fourth** candidate (F5) and take the same treatment.
- **If established false or indistinguishable:** record that, and amend nothing.
- ⚠ **This plan does not get to conclude it either way from reading.** F4 says the comparator cannot return green; it does not by itself say those specific consumers had no real drift. Those installs may have had both.

### OQ-3 — Does `install.sh:364`'s presence guard stay?

The guard leaves an existing root `constitution.md` alone (F3). Under D2(a) the canonical text would arrive by a different path (`.devforge/template/`), so the guard's role changes.

- **RECOMMEND: it stays, untouched.** Its job is brownfield safety — never overwrite a user's constitution — and that job is unchanged by anything here. D2(a) makes it irrelevant to the text source rather than wrong.
- **Alternative:** drop the root copy entirely, since after D2(a) nothing reads it as a source and `render` overwrites it anyway. That is a real simplification and it is **out of this plan's scope**: the root copy is what a freshly installed, never-constituted project has as its constitution, and removing it is a separate decision with its own blast radius.
- **Recorded either way:** `install.sh:371`'s drift-check call sits in the guard's `else` branch, so anything done to the guard touches when the drift check runs.

---

## Phase 0 close record

**Pending.** Nothing is ratified. **No build phase may start until this section carries an outcome — ratified, amended or declined — for every one of D1–D7 and OQ-1–OQ-3.**

When it closes it must state, following the house pattern:

- **Each** of D1–D7 and OQ-1–OQ-3 by name, with its outcome. **No item silently omitted** — check by NAME, never against a range (plan 100's Phase-4 tripwire: a range reads as complete while the enumeration beside it drops a member).
- Whether **per-item deliberation was supplied**, and whether the close was an **explicit pick or a delegation**.
- That **every decision keeps its counter-argument** — a ratified decision with its counter-argument deleted cannot be re-opened honestly.
- **Which files each outcome puts in scope**, per phase.
- ⚠ That **ratification changes no evidence class**: F1 observed once, F2–F4 found by reading, nothing measured.

⚠ **D5 must be answered before D2, D3 and D4 are read as settled.** If the close is a blanket ratification, it still records that ordering, because D2's, D3's and D4's recommendations are each explicitly conditional and a blanket close does not discharge a condition.

---

## Phases

Every phase names the decision it depends on. **A phase whose decision is unratified does not start**, and no phase assumes an answer.

### Phase 0 — Ratification

D1–D7 and OQ-1–OQ-3 each get an outcome in `## Phase 0 close record`.

#### Verify

- The record names **each** of D1–D7 and OQ-1–OQ-3 with its outcome, checked by name.
- It states whether per-item deliberation was supplied, and whether the close was a pick or a delegation.
- Each decision still carries its counter-argument.
- **It records that D5 was decided before D2, D3 and D4 were treated as settled**, or, if it did not, says so.
- It names the files each outcome puts in scope.

### Phase 1 — The label (F1)

**Depends on: D1 including it. Depends on nothing else, and blocks nothing.**
**Route: instruction-author → instruction-reviewer. Instruction-only — no `.py` file changes.**

⚠ **This phase MAY ship alone**, before or without any other phase in this plan. It is the only part of this subject a user has met.

- `src/commands/constitute/main.md` — the seven `Section 3.5` sites, **with the user-facing echo line the priority**: whatever a reader of that line is told must not collide with the constitution's own §3.5. The three sites that already disambiguate in model-facing prose keep their disambiguation.
- `src/CLAUDE.md` — the `#### /devforge:constitute` catalog entry's clause.
- **Nothing about the forcing-functions mechanism changes.** No verb, no key, no setter, no config shape.

#### Verify

- `grep -rn "Section 3.5" src/` returns no site that names the forcing-functions config block by a `3.x` number, or returns nothing.
- Every surviving mention of the block states that it is a config block and not a numbered `constitution.md` sub-section — **including the user-facing echo line**, which does not today.
- `grep -rn "forcing_functions" src/devforge/lib/_constitute/` is unchanged: `git diff --stat src/devforge/lib/` is empty for this phase.
- The live-spec tests are green: `tests/lib/test_agent_reachability.py`, `tests/lib/test_memory_lane.py`, `tests/scripts/test_claude_emitter.py`.
- instruction-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 2 — Rule identity and comparison keying (F4)

**Depends on: D5, then D4.** Not startable while either is open.
**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn.**

- The schema change D5 ratifies, across the surfaces its blast-radius list names: `add-rule`'s CLI surface, `validate`'s Dim 4, `render`, both sides of `_universal.py`, and the tests.
- The comparator keys on whatever D4 ratifies, in `_cmds_quality.py`.
- ⚠ **If D5 is ratified (b) — no identity field — this phase is D4's repair alone**, and its Verify drops every schema bullet. The phase does not silently do (a) anyway.

#### Verify

- **The two sides mean the same thing**, demonstrated by a test that builds a consumer state through the real CLI and asserts the comparator's canonical and consumer key sets are equal for at least one section outside §3.6 and §4.x, and for §3.6 and §4.1 as well.
- `validate`'s composite on a fully-populated real-producer state is **unchanged** from before this phase, or the change is stated with the number (F7: Dim 4 carries weight 0.20 against a 0.95 gate).
- `render` output on a fully-populated state is byte-identical to before this phase, or every difference is stated.
- The targeted suite, then the full `tests/lib` suite, is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

### Phase 3 — Canonical text delivery and seeding (F3)

**Depends on: D2 and D3, and D2 depends on Phase 2's outcome (D5).** Not startable while any is open.
**Route: python-engineer → python-reviewer for the helper work; instruction-author → instruction-reviewer for any `install.sh`-adjacent doc text.**

- The carrier D2 ratifies. Under (a): one added line in `install.sh`'s snapshot block at `:432-434`, copying from `$TEMPLATE_DIR/src/constitution.md` directly (`install.sh:365`'s pattern) and **not** from `$TARGET_DIR` the way the block's existing two lines do.
- The seeding route D3 ratifies. Under (a): a new verb that writes all eleven universal sections into `.devforge/constitute.json` from the canonical source, with the helper owning numbers, headings, tags and identities.
- The `/devforge:constitute` spec is wired to call it, at a phase that runs before Section 3's and Section 6's echoes.

#### Verify

- A fresh `reset` followed by the seeding route produces a state in which **`_extract_universal_rules_from_state` returns all eleven `_UNIVERSAL_SECTIONS` keys**, each with non-empty rules.
- `forge-internal:verify-universal-defaults` against that state and the canonical file **exits 0 with zero findings** — the first time any real-producer state has been fed to that verb.
- The canonical text reaching the consumer is the shipped template's, not a rendered artifact: the source path is asserted in a test, and `install.sh:364`'s presence guard is untouched (OQ-3) or its change is stated.
- The 27-subcommand count is restated as whatever it now is, **counted live from `add_parser(` call sites, never incremented from memory.**
- Full `tests/lib` suite green; python-reviewer SHIP-READY or every finding fixed.

### Phase 4 — The numbering and the ranges (F2)

**Depends on: D7, and on Phase 3 having landed.**
⚠ **HARD ORDERING RULE: this phase MUST NOT ship before Phase 3.** With correct numbers and no body-text source, the model produces the canonical heading at the canonical number and invents the body — quieter than today's absence, not louder. **Correct numbers without delivery is a worse state than the current one, because it removes the MISSING signal without supplying the content.**
**Route: instruction-author → instruction-reviewer. Instruction-only.**

- `constitute/main.md:103` — the Section 3 count and the composed sub-section list, per D7.
- `constitute/main.md:134` — the Section 6 list, so 6.2 / 6.3 / 6.4 name the canonical headings.
- `references/section-shapes.md` — the Section 3 *"Shape"* line and its *"Common sub-sections"* list; the Section 6 *"Common sub-sections"* list; the *"Function Length"* example universal dimension; and the CBM-first protocol rule's anchor, which today names a *"Section 3 Documentation sub-section"* that does not exist in the canon.
- The echo/override text D6 ratifies.
- ⚠ **The CBM-first rule needs a home, not just a corrected name.** It is an `[enforced]` rule with a real trigger; re-anchoring it is a decision about which sub-section owns it, and this phase makes it explicitly rather than by renaming a string.

#### Verify

- `grep -rn "3.5 Documentation\|3.6 Function Length\|6.2 Read Before Write\|6.3 Search Before Building\|6.4 One Task At A Time\|Function Length / Complexity" src/commands/constitute/` returns nothing.
- `grep -rn "4-7 sub-sections\|Shape\*\*: 4-7" src/commands/constitute/` returns nothing.
- Every universal number named in `constitute/main.md` and `references/section-shapes.md` matches a heading in `src/constitution.md` at that number — checked pairwise, not by count.
- The CBM-first protocol rule names a sub-section that exists in the canon, and the phase records **which** and **why**.
- `git log` shows Phase 3's commit before this one. **Stated, not assumed.**
- The live-spec tests are green; instruction-reviewer SHIP-READY or every finding fixed.

### Phase 5 — The tests onto the real-producer principle (OQ-1)

**Depends on: OQ-1, and on Phases 2 and 3 having landed** (a real-producer in-sync fixture is unbuildable before them).
**Route: python-engineer → python-reviewer.**

- The `TestForgeInternalVerifyUniversalDefaults` fixtures, per OQ-1.
- `test_verify_universal_defaults_passes_with_38_in_sync` and `test_verify_universal_defaults_detects_missing_38`, which share the same hand-authored builder or a bare `default_state()` (F5).
- `_build_in_sync_constitute_json`'s docstring, whose *"Fixture strategy"* paragraph explains a constraint this plan removes.

#### Verify

- **At least one test feeds a state built through the real CLI to `verify-universal-defaults` and asserts exit 0.** That test is named in this phase's record as the one that would have caught F4.
- The MISSING and DRIFT tests still fail-when-they-should: one asserts MISSING on a genuinely absent section, one asserts DRIFT on a genuinely altered body, **both on real-producer states**.
- No surviving fixture writes a value into `tag` that `add-rule` would reject. `grep -n '"tag": r\["tag_or_label"\]' tests/lib/test_constitute_helper.py` returns nothing, or every survivor is stated with its reason.
- Full `tests/lib` suite green; python-reviewer SHIP-READY or every finding fixed.

### Phase 6 — The drift-claim question (OQ-2)

**Depends on: OQ-2, and on Phase 5 (the before/after run needs the real-producer fixture).**
**Route: instruction-author → instruction-reviewer for the amendments; the run itself is an observation recorded in this plan.**

- Run the before/after OQ-2 names and **record the result as a fact with its numbers**, in this plan's build record.
- If established: dated amendments — never rewrites — at plans 86, 89 and 99's drift claims, and at `44-CONSTITUTION-DRIFT-WIRING-PLAN.md`'s *"~30 MISSING"* / *"29 MISSING findings"* records (F5).
- If not established, or indistinguishable: record that, and amend nothing.

#### Verify

- The run's result is recorded as a NUMBER on both sides (findings before, findings after), not as a characterization.
- Every amendment is **dated and additive**; no ratified sentence in plans 44, 86, 89 or 99 is rewritten or deleted.
- ⚠ The amendments say what was established and what was not. **"Indistinguishable" is a legitimate result and is recorded as one**, not smoothed into either conclusion.
- `grep -rn "designed consumer drift\|verify-universal-defaults" --include=*.md .` is classified in full: each hit is an amended site, history, or this plan's own quote of one.

### Phase 7 — Docs sweep

**Route: instruction-author → instruction-reviewer. Docs only.** Apply F8 before touching any ledger.

- `CHANGELOG.md` — a new entry under `## [Unreleased]`, **evidence class first and honest bounds last**.
- `DEVELOPMENT-STATUS.md` — an edit or a recorded verified no-op.
- Repo `CLAUDE.md` — **the "Where to find what" router's constitute / forcing-functions rows ONLY**: an edit or a recorded verified no-op. ⚠ **No index line goes here, and no pointer to the archive either** — that file carries no plan status at all.
- `PLAN-STATUS-ARCHIVE.md` — **two sites in one file**: this plan's one-line entry in `## Index`, in the house shape its neighbours there use, and a new full entry in `## Entries` in the archive's house shape. `## Entries` is the authority; the `## Index` line summarizes it and never competes with it.
- `README.md` — an edit or a recorded verified no-op.

#### Verify

- Every site is recorded as an **edit or an explicit verified no-op, with the grep that shows it.**
- `grep -rn "104-UNIVERSAL" --include=*.md .` returns `PLAN-STATUS-ARCHIVE.md` **twice — once under `## Index`, once under `## Entries`** — plus this file, at minimum. ⚠ It returns **no** repo `CLAUDE.md` hit; one there is a line this phase must not have written.
- No summary anywhere claims consumer validation. **"Built and reviewed" is the ceiling** until Phase 8 runs.
- The evidence class is attached at every site: F1 observed once, F2–F4 found by reading, nothing measured.
- No tracked file names a client, a client component, a client ticket or a benchmark path.

### Phase 8 — Consumer e2e — user-driven HARD GATE, NOT run

**Everything above is build-verified at best, never consumer-validated, until this phase runs.**

- **Fixture:** a testForge20 install. **The frozen benchmark install is never touched.**
- The anchors are known-answer cases, **scored in PAIRS**:

1. **A fresh `/devforge:constitute` run on a constituted-from-scratch fixture** → the rendered `constitution.md` carries §3.5, §3.6, §3.7, §3.8, §6.1, §6.2, §6.3 and §6.4 **at those numbers with those headings**, and the bodies match the canonical file. **PAIRED WITH 2.**
2. **`forge-internal:verify-universal-defaults` against that same install** → **exit 0, zero findings.**
3. **The same install with one universal rule deliberately altered** → exit 2 with **exactly that section** in the findings, and no other.
4. **A `/devforge:constitute` run read by a human at the forcing-functions echo** → the user-facing line does not name the block by a `3.x` number, and nothing in the transcript invites a reader to confuse it with §3.5. (Phase 1's anchor; it stands alone if Phase 1 ships alone.)
5. **An `update.sh` run against a constituted install with nothing drifted** → **no constitution-drift warning at all.** ⚠ This is the anchor that tests F5's user-visible consequence, and it is the only one that would show the warning noise gone.

#### Verify

- Every anchor is scored **explicitly** — stated, not summarized — with the pair scored together.
- **If an anchor fails,** record the negative with the artifacts and name the mechanism before proposing any fix: a wrong number or heading is D7 / Phase 4; an invented body is D2 / D3 / Phase 3; a false MISSING is D4 / D5 / Phase 2; a false green on anchor 3 is a comparator that stopped comparing; a surviving label collision is Phase 1. **They have different fixes.**
- **A clean run shows the chain behaves on planted fixtures, never that any of these gaps cost anything** — F1 is the only observed item, and it is a label, not a mechanism.

---

## Honest bounds

- **No consumer incident for F2, F3 or F4.** The only observed thing is F1's label confusion in a real run. F2–F4 were found by reading. **Nothing was measured** — not how many consumers have a wrong-numbered §3.5, not how much universal text is missing from any install, not how often the drift warning fires.
- **The framework currently has no production installs, only test ones** (maintainer, 2026-09-20). **So there is no backward compatibility to preserve and no migration owed** — which is the reason the more invasive options (D4(a), D5(a)) stay on the table rather than losing to the cheapest compatible repair. ⚠ If that stops being true before this plan ships, D4 and D5 must be re-argued, not inherited.
- **A green `verify-universal-defaults` test run is not evidence the detector works.** Today five such tests pass against a comparator that cannot return green on a real install (F4, F5). Only a real-producer in-sync fixture asserting exit 0 is evidence, and it does not exist yet.
- **F5's artifact question is not settled by this plan's reading.** F4 says the comparator cannot return green; it does not say the specific installs plans 44, 86, 89 and 99 describe had no real drift. They may have had both. OQ-2 establishes it by a run or records that it could not.
- **Nothing mechanical checks that the model composed the canonical text.** After every phase here, `validate`'s dimensions and `verify-universal-defaults` are the only nets, the second is advisory and WARN-only at install/update time, and neither runs inside a `/devforge:constitute` session at the moment a sub-section is composed.
- **D6(a) knowingly ships an unsilenceable warning** for a user who deliberately overrides a universal rule, and a warning that is learned-past trains a user past the real ones too. Accepted, with (c) recorded as the named strengthening arm and its trigger stated.
- **Phase 4 without Phase 3 is worse than today.** Correct numbers with no text source replaces a loud absence with a quiet invention. This is an argument from reasoning, not from an observed run.

---

## Tripwires

- **Plan 75's tripwire, both halves: zero new `verify-*` gates, zero new check numbers, zero new hard-fail validators.** This plan repairs an existing advisory detector and adds no gate. `verify-universal-defaults` stays WARN-only and fail-soft at `install.sh` / `update.sh`; nothing here makes it block.
- **No edit to `src/constitution.md`.** The canonical file is the thing everything else is measured against; editing it inside this plan would move the target mid-repair. Any constitution amendment is a separate plan with its own designed-drift note.
- **No back-porting into shipped installs.** They arrive via `install.sh` / `update.sh`. The frozen benchmark install is never touched.
- **Python is confined to Phases 2, 3 and 5** (delivery, keying, tests). Phases 1, 4, 6 and 7 are instruction and docs only.
  - Python goes python-engineer → python-reviewer, with a test for every function, run in the same turn.
  - Every markdown edit goes instruction-author → instruction-reviewer.
  - Every new Claude Code fact is checked through `claude-code-guide`.
- **No change to §4.1–§4.3's path.** They travel `add-pattern-rule`, which appends to a named `patterns_and_antipatterns` bucket and records that bucket name, never a number; their numbers are fixed in `src/constitution.md`'s own `### 4.1`, `### 4.2` and `### 4.3` headings, and no number here is ever composed by the model. D4 and D5 touch how their rules are **compared** — the side `_PATTERNS_BUCKET_TO_SECTION` serves — never how they are produced.
- **Counts are counted live, never incremented from memory.** The 27 subcommands, the eleven `_UNIVERSAL_SECTIONS` entries, the eight Section 3 sub-sections, the five `verify-universal-defaults` tests — re-derive each one at build time and state the number you counted.
- **No `disable-model-invocation` change.** `/devforge:constitute` stays human-typed-only; this plan moves no flag and contributes no count delta.

---

## Non-goals

- **A new `verify-*` gate or a new check number.** Plan 75's tripwire, both halves.
- **Editing `src/constitution.md`.**
- **Back-porting into shipped installs**, and anything specific to the frozen benchmark install.
- **Changing §4.1–§4.3's production path** (`add-pattern-rule` appending to the `patterns_and_antipatterns` bucket).
- **Making `verify-universal-defaults` blocking.** It is advisory at `install.sh` / `update.sh` and stays advisory.
- **Removing the root `constitution.md` copy** (OQ-3's alternative) — a separate decision with its own blast radius.
- **Rewriting any ratified sentence in plans 44, 86, 89 or 99.** OQ-2's remedy is dated additive amendments only.
- **Deciding whether prior drift findings were artifacts, from reading.** OQ-2 establishes it by a run or records that it could not.
- **Touching a plan file this session did not create.** Ownership is established from `git status` and from which sessions are active in this checkout, never from a plan's number (F8).

---

## Context for next session

⚠ **Evidence class, repeated: F1 was observed ONCE, in a real run, as a label confusion. F2, F3 and F4 were found by READING. Nothing was measured, and no incident stands behind the mechanism half of this plan.** ⚠ All line digits drift — grep the quoted text.

**The one sentence that governs everything here:** the chain that puts universal sub-sections into a consumer's `constitution.md` is unclosed at every link — wrong numbers, no text source, a detector that cannot return green, and tests that hide it.

### The 2026-09-20 reverted session — what happened and what carries forward

On 2026-09-20 a session fixed F1 and F2 directly in the tree: the user-facing echo line, all seven label sites, the canonical numbers in both commands and the reference file, plus two consequential doc fixes. **Every one of those edits was then reverted**, when the maintainer observed the work should have been a plan rather than a series of audit fixes. **Nothing from that session survives in the tree**, and this plan assumes none of it — the facts above were re-checked against the live tree after the revert.

Two things from it carry forward, and both are load-bearing:

1. **F4 was discovered during that session** and is recorded in this project's memory as `verify-universal-defaults-broken`. That memory note and this plan are the only places it exists.
2. **An attempted fix of F2 alone would have changed the failure mode rather than removing it.** With correct numbers and no body-text source, the model produces the canonical heading at the canonical number and **invents** the body — which is **quieter than the current absence, not louder**, and downgrades the detector's signal from MISSING to DRIFT. **That is the argument for treating delivery (F3) as inseparable from numbering (F2)**, and it is why Phase 4 carries a hard ordering rule rather than a preference.

### Traps

**Trap 1 — reading "Section 3.5" as the constitution's §3.5.** In `constitute/main.md` and `src/CLAUDE.md` it names the **forcing-functions config block**, which targets a top-level `.devforge/constitute.json` key and can never render as a numbered sub-section. The constitution's §3.5 is *Universal Code Quality*. This collision is F1 and it is the whole of Phase 1.

**Trap 2 — fixing the numbers first.** See above. Phase 4 must not ship before Phase 3.

**Trap 3 — trusting a green `verify-universal-defaults` suite.** Five tests pass today against a comparator that cannot return green on a real install. Until a real-producer in-sync fixture asserts exit 0, a green suite is evidence of nothing here.

**Trap 4 — assuming `verify-universal-defaults` is maintainer-only.** `scripts/constitution-drift-check.sh` calls it from `install.sh` and `update.sh`. Under F4 every constituted consumer sees its warning on every update. It is WARN-only and fail-soft — it never blocks — but it is user-visible.

**Trap 5 — concluding that plans 86 / 89 / 99's designed drift was an artifact.** F4 makes it a candidate, not a finding. OQ-2 settles it with a before/after run or records that it could not. `44-CONSTITUTION-DRIFT-WIRING-PLAN.md`'s *"~30 MISSING"* is a fourth candidate on the same footing — **a count F4 predicts for an in-sync install as readily as for a drifted one.**

**Trap 6 — deciding D2 before D5.** D5 decides whether a rule has an identity separate from its tag; that changes what the canonical-text carrier must carry. A carrier chosen first is a carrier chosen blind.

**Trap 7 — smuggling a name into `tag`.** It is exactly what the hand-authored fixtures do, and it is what the real CLI rejects. `validate`'s Dim 4 is mechanical at threshold 1.0 with weight 0.20 against a 0.95 human gate — a smuggled label costs the composite and a non-enum value fails outright.

**Trap 8 — treating §4.1–§4.3 as part of the numbering problem.** Their numbers are fixed in `src/constitution.md`'s own `### 4.1`, `### 4.2` and `### 4.3` headings, and `add-pattern-rule` records a bucket name rather than a number — no number here is composed by the model. `_PATTERNS_BUCKET_TO_SECTION` (`_schema.py`) is on neither the setter path nor the render path; its one use site is the consumer-side extractor in `_universal.py`. So they share the **comparison** defect (their consumer-side key is `rule.tag` too) and none of the composition defect.

**Trap 9 — reading `install.sh`'s root `constitution.md` copy as a text source.** It is presence-guarded, uninstructed, and on any re-run holds the previously rendered artifact. F3.

**Trap 10 — a clobbered ledger edit.** Other sessions build in this checkout, and their plan files appear, move and get renumbered without warning (F8). Re-read `git status`, read each ledger live, commit by explicit path, and **never touch a plan file this session did not create** — ownership is established from `git status` and from which sessions are active, never from a plan's number.

### File anchors

- `src/commands/constitute/main.md` — the four input captures; the Section 3 and Section 6 compose paragraphs; the per-section echo template and its override footer; the Section 3.5 echo template and its setter block; the render contract paragraphs.
- `src/commands/constitute/references/section-shapes.md` — the Section 3 and Section 6 blocks; the universal-dimension example; the CBM-first protocol rule.
- `src/constitution.md` — **read-only here.** §3.1–§3.8, §6.1–§6.6, and the `## Rule Tags` section.
- `src/devforge/lib/_constitute/` — `_universal.py` (both comparison sides), `_cmds_quality.py` (the comparator), `_schema.py` (`_UNIVERSAL_SECTIONS`, `_PATTERNS_BUCKET_TO_SECTION`, the `rule_tag` enum), `_validate_metrics.py` (Dim 4), `_cmds_render.py` (`section_bucket_keys`), `_cli.py` (the 27 subparsers).
- `tests/lib/test_constitute_helper.py` — `TestExtractUniversalRulesFromState`, `TestForgeInternalVerifyUniversalDefaults`, `_build_real_constitute_state`, `_build_in_sync_constitute_json`, and the two §3.8 verify tests.
- `install.sh` — the constitution presence guard and drift-check call; the `.devforge/template/` snapshot block.
- `update.sh` and `scripts/constitution-drift-check.sh` — the drift-check wiring.
- `src/CLAUDE.md` — **read-only except Phase 1's one clause** in the `#### /devforge:constitute` entry.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation, including a reverted session whose edits are not in the tree.
2. **Check `## Phase 0 close record` first.** If it still reads *Pending*, nothing is ratified and **no build phase may start.**
3. **Re-verify F1–F8 against the live tree.** Grep the quoted text, never the digits: `Section 3.5 echo template`, `proposes for Section 3.5`, `Compose 4-7 sub-sections`, `Common sub-sections: Minimal Changes`, `Function Length / Complexity`, `Section 3 Documentation sub-section`, `"tag_or_label": heading`, `r.get("tag", "")`, `Fixture strategy`, `Real-producer principle`, `forge_check_constitution_drift`, `leaving as-is`, `.devforge/template/.claude/agents`. ⚠ After a build phase some of these strings are gone by design; zero hits is then the built state, not a regression.
4. **Answer D5 before you read D2, D3 or D4 as settled.** A blanket close does not discharge D2's, D3's or D4's explicit conditions.
5. **Build order:** Phase 1 is independent and may ship alone. Phase 2 before Phase 3; **Phase 3 before Phase 4, without exception**; Phases 2 and 3 before Phase 5; Phase 5 before Phase 6; Phase 7 last, because it records what the others did.
6. **Route every edit through the house flow:**
   - python-engineer → python-reviewer for every Python edit, with a test per function, run in the same turn;
   - instruction-author → instruction-reviewer for every markdown edit;
   - `claude-code-guide` for every new Claude-Code-integration fact.
7. **Commit by explicit path, never `git add -A`.** Re-read `git status` first (F8), and touch no other session's plan file.
8. **After each phase, cross-check.** Grep every verb, key, section number and heading touched — `verify-universal-defaults`, `_UNIVERSAL_SECTIONS`, `tag_or_label`, `Section 3.5`, `3.8 Design Fidelity`, `seed-universal` if it exists — and fix any dangling reference in the SAME change.
9. **Run Phase 7, then leave Phase 8 to the maintainer.**
10. **Keep the evidence class attached.** Any summary of this plan repeats it: **F1 observed once as a label confusion; F2, F3 and F4 found by reading; nothing measured.**
