# 104 — Universal Sections Integrity Plan

**Created**: 2026-09-20
**Status**: **Phases 1–6 BUILT — Phase 1 on 2026-09-24, Phases 2–6 on 2026-09-25. Phase 7, the docs sweep, is PENDING. Phase 8, the user-driven consumer e2e HARD GATE, is NOT run — so "built and reviewed" is the ceiling of every claim here: nothing this plan ships is consumer-validated.** *(corrected 2026-09-25 at build — until the build this line read "Build phases MAY start. NOTHING IS BUILT.")* Commits: Phase 0 close `4c61af4`; Phase 1 `9981148`; Phase 2 `01e3d3a`; Phase 3 `787cf72`; Phase 4 `c76905d`; Phase 5 `760b8b7`; Phase 6 — the Phase 6 commit, which carries this line. Each built phase carries a `#### Phase N build record` directly after its `#### Verify`: its commit, what was built, how its Verify lines were met, what is on record of its review, its test counts, and every build-time decision and departure. ⚠ **One maintainer decision was taken mid-build, on 2026-09-25: `drop-rule` and `drop-section` were added** (`#### Phase 3 build record — 2026-09-25`). **Phase 0 CLOSED 2026-09-24 by a blanket maintainer directive — every item ratified as recommended (D2 and D3 by their standing text, see the record).** `## Phase 0 close record` — not the drafting-time text under `## Decisions to ratify` — says what each phase must do. ⚠ **Neither the close nor the build changes the evidence class** (the paragraph below). **Re-checked against the live tree 2026-09-24 — see `### Re-check (2026-09-24)`**; that re-check added F9–F11, corrected false sentences in place and re-opened two recommendations, and it ratified nothing.

⚠ **Evidence class, to be repeated in every summary of this plan: ONE observed thing only — a user hit F1's label confusion in a real run and asked whether it was a bug. F4, F9, F10 and F11 were REPRODUCED on 2026-09-24 on a scratch state built through the real CLI — reproductions, not consumer incidents. F2 and F3 were found by READING. Nothing was measured on any consumer, no consumer incident stands behind any of them, and a clean consumer run at the end of this plan would show the chain behaves on planted fixtures, never that any of these gaps cost anything.**

**The one sentence that governs everything here:** the chain that puts universal sub-sections into a consumer's `constitution.md` is unclosed at every link — the spec names wrong numbers, nothing supplies the canonical body text, the render cannot reproduce that text, the drift detector cannot return green, and the tests hide it.

---

## Origin & evidence

- **The one observed thing (F1).** A user reading a real `/devforge:constitute` run met the string *"Section 3.5"* in the user-facing echo, compared it to the constitution's own §3.5, and asked whether it was a bug. It is a label collision, not a mechanism defect — and it is the only part of this plan anyone has ever reported.
- **F2, F3 and F4 were found by reading**, in the session that followed that question. Each is recorded below with the `file:line` it was checked at on 2026-09-20. **F4 was then reproduced on 2026-09-24**, together with three new facts F9–F11, on a scratch state built through the real CLI (`### Re-check (2026-09-24)`). **None was observed failing on a consumer, and no count, rate or cost was measured on any consumer** — the re-check's numbers are a scratch state's.
- **F4 is separately recorded in this project's memory** as `verify-universal-defaults-broken` (memory file present 2026-09-20). That record and this plan are the only places it exists.
- **The 2026-09-20 reverted session.** See `## Context for next session` — Facts 1 and 2 were fixed in the tree that day and every edit was then reverted, on the maintainer's observation that the work should have been a plan rather than a series of audit fixes. **Nothing from it survives in the tree**, and this plan is written as if none of it happened, because in the tree none of it did.

### Verified structure (2026-09-20)

Every fact below was checked against the tree on 2026-09-20. ⚠ **Line digits drift — grep the quoted text, never the digits.**

#### F1 — the "Section 3.5" label collision

- **Seven sites in `src/commands/constitute/main.md`** (grep `Section 3.5`): the echo-template heading `### Section 3.5 echo template (Forcing Functions — config block, not a constitution.md sub-section)` (`:235`), the template body (`:237`), **the USER-FACING echo line** *"Here's what /devforge:constitute proposes for Section 3.5 — Forcing Functions [config-block]:"* (`:255`), the setter-plan bullet (`:329`), the setter-call block (`:406`), a comment in that block (`:433`), and one more at `:563`.
- **One site in `src/CLAUDE.md`** (`:129`, the `#### /devforge:constitute` catalog entry): *"Its Section 3.5 forcing-functions config-capture offers the `design_token_provenance` rule …"*. This file is emitted into every consumer project.
- **The real §3.5** is `src/constitution.md:62` — `### 3.5 Universal Code Quality [universal]`.
- **The block is structurally not a numbered sub-section.** It targets the top-level `forcing_functions` key in `.devforge/constitute.json`, and the render walk — `_render.py`'s `_render_constitution` — reads only `architecture_rules`, `code_quality_standards`, `patterns_and_antipatterns`, `domain_rules`, `workflow_rules` and `scaffolding_guide`; a grep for `forcing` in `_render.py` returns nothing (read 2026-09-24). A `forcing_functions` entry can therefore never render as a `3.x` sub-section. (`_cmds_render.py`'s `section_bucket_keys` list is not the render walk: it sits inside `cmd_verify`, under the comment *"Check 2: Section arrays"*.)
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

The two comparison sides build the per-rule key from different things. **Found by reading on 2026-09-20; reproduced on 2026-09-24** on a scratch state built through the real CLI, not a consumer — exit 2, 32 findings, all MISSING, 0 DRIFT (`### Re-check (2026-09-24)`).

- **Canonical side, `_universal.py:84`** (the default branch of `_parse_universal_blocks`): `rules = [{"tag_or_label": heading, "body": body_text}]` — **the key is the SECTION HEADING**, e.g. `"Universal Code Quality"`. (§3.6 takes `_split_design_principles` and §4.1–§4.3 take `_split_bullet_rules`; both produce bold sub-labels as keys, e.g. `"Single Responsibility"`.)
- **Consumer side, `_universal.py:270`**: `{"tag_or_label": r.get("tag", ""), "body": r.get("text", "")}` — **the key is `rule.tag`**, a member of the `rule_tag` enum `{extracted, enforced, universal, project-specific}` (`_schema.py:268`). The patterns-bucket branch at `:281` does the same.
- **`_cmds_quality.py:184-212`** builds both dicts keyed on `tag_or_label` and reports `MISSING` for every canonical label absent from the consumer keys, then `DRIFT` on a body mismatch. **`heading` is carried in the return shape by `_universal.py:86` and never compared — the string `heading` does not appear in `_cmds_quality.py` at all.**
- **No enum value equals a heading string, so every universal section reports MISSING even for a perfectly composed consumer.** §3.6 and §4.1–§4.3 mismatch for the same reason with different canonical keys.

**Two filters compound with F2, checked at `_universal.py:259-265`.** The consumer side skips any section whose `tag != "universal"` and any section whose `number` is not in `_UNIVERSAL_SECTIONS` (`_schema.py:296-300` — a closed eleven-entry tuple: §3.5–§3.8, §4.1–§4.3, §6.1–§6.4). **So a sub-section composed at a wrong number (F2) never enters the comparison either** — the same `MISSING` line, from a second independent cause. **A third independent cause is F9** (the canonical parser swallows `## 4.` into §3.8's body). **Fixing any one of the three — F4's keying, this filter, F9's section boundary — alone does not make the detector green.**

**The tests do not catch this, and say why in their own docstring** — `tests/lib/test_constitute_helper.py`, `class TestForgeInternalVerifyUniversalDefaults`: *"All 3 tests use hand-authored constitute.json fixtures because the ``add-rule`` setter constrains ``--tag`` to enum values, so principle names like "Single Responsibility" cannot be stored via the CLI."* The shared builder `_build_in_sync_constitute_json` writes `{"tag": r["tag_or_label"], "text": r["body"]}` for all eleven sections — **the canonical heading into the `tag` field, a state the real CLI rejects** (`add-rule` validates `--tag` against the enum; `test_invalid_tag_exits_2`).

⚠ **This violates the repo's own real-producer principle, and it is recorded in that class's docstring as a fixture *strategy*, not as a defect.**

#### F5 — what F4 means for anything that ever ran the detector

- **The detector is not maintainer-only in practice.** `scripts/constitution-drift-check.sh:54` invokes `forge-internal:verify-universal-defaults`, and that function is sourced and called from **`install.sh:371`** (the brownfield *"leaving as-is"* branch) and **`update.sh:247`** (every update of a constituted consumer). It is **WARN-only and fail-soft** — on exit 2 it prints *"⚠ Constitution out of date — framework law has changed since this project was constituted:"* with a per-section rule count, and returns 0.
- **So under F4 every constituted consumer sees that warning on every update, naming every universal section, regardless of whether anything drifted.**
- **There are five `verify-universal-defaults` tests, not three.** Beyond the class above, `test_verify_universal_defaults_detects_missing_38` builds a bare `default_state()` (nothing populated) and asserts `MISSING §3.8` — which passes trivially — and `test_verify_universal_defaults_passes_with_38_in_sync` calls the **same** hand-authored `_build_in_sync_constitute_json`.
- **The real-producer path exists for the extractor and never reaches the comparator.** `TestExtractUniversalRulesFromState` opens with *"Real-producer principle: fixture states are built via the actual constitute_helper CLI (reset + add-section + add-rule + add-pattern-rule) rather than hand-authored JSON"*, and `test_happy_path_real_producer` asserts `result["§3.5"]["heading"] == "Universal Code Quality"` — **it reads the `heading` key, which is the one the comparator ignores.** No test feeds `_build_real_constitute_state`'s output to `verify-universal-defaults`.
- **Shipped user-facing text describes a warning that does not behave that way** (read 2026-09-24). `README.md` gained, in the 2.0.12 release commit `e2a3862` (committed 2026-09-23, after this plan was drafted): *"`constitution.md` is project-owned and an update never rewrites it. When a release changes a universal constitution section, the update prints a WARN-only drift notice naming the drifted sections and exits normally; re-run `/devforge:constitute` to adopt the new wording."* Under F4 — reproduced 2026-09-24 on a scratch state — the notice names all eleven sections on every update of every constituted install, whether or not a release changed any, and **re-running `/devforge:constitute` cannot clear it** (F4's keying, the F2 filter, F9's boundary).
- **Two false comments sit beside it** (read 2026-09-24). `scripts/constitution-drift-check.sh`: *"Check A — universal-section drift. Exit 2 == real drift"*, and its printed remediation *"Fix: re-run /devforge:constitute to re-synthesize constitution.md + forcing-function config."* — which cannot clear the universal-section half of the warning today. `update.sh`: *"Project customizations live in CLAUDE.md / constitution.md / agents — those still three-way merge upstream."* (grep `Project customizations live in`; the sentence wraps across two comment lines) — false for `constitution.md`, which `src/manifest.json` lists under `projectOwned` (*"NEVER overwrite"*) and which no line of `update.sh` copies or merges.

⚠ **The consequence this plan must state and must NOT conclude.** The "designed consumer drift" that plans 86, 89 and 99 each tell consumers to expect may be an ARTIFACT of F4 rather than real drift. **This plan does not get to decide that** — OQ-2 owns it, and it is established by a run, not by reading. **Where each claim lives** (named 2026-09-24 — grep the quoted text):

- `86-FOWLER-REFACTORING-GAPS-PLAN.md`'s claim lives **only** in `CHANGELOG.md` under `## [2.0.10]` (grep `Consumer-install drift, by design`). The plan file itself has zero `verify-universal-defaults` hits.
- `89-TEST-FOUNDATION-HARDENING-PLAN.md`'s claim is in that plan file (grep `verify-universal-defaults`) **and** in `CHANGELOG.md` under `## [2.0.10]` (grep `Consumer-install drift is expected`).
- `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md`'s claim is in that plan file (grep `Designed consumer drift, not a regression`) **and** in `CHANGELOG.md` under `## [2.0.12]` (grep `Designed consumer drift.`).
- **A fourth candidate** is recorded here so it is not missed: `44-CONSTITUTION-DRIFT-WIRING-PLAN.md` reports *"~30 MISSING universal rules across §3.5/§3.6/§3.7/§3.8/§4/§6"* and *"validated on testForge20 with exit 2 + 29 MISSING findings"* — a count that F4 predicts for an in-sync install just as well as for a drifted one, so **that observation cannot distinguish the two and is not evidence either way.**
- **A fifth candidate appeared after this plan was drafted:** `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md` (created 2026-09-21), whose ratified D7 declined a §6.1 edit partly so that *"no fourth `verify-universal-defaults` / update-time drift finding is created for installs constituted earlier"* — a cost argument that rests on the detector's findings being meaningful. **Recorded, NOT reopened by this plan:** it is another plan's ratified decision, and OQ-2 only records whether its cost premise held.

**Released `CHANGELOG.md` sections are not edited in place in this repo**, so the `## [2.0.10]` and `## [2.0.12]` claims can only ever be corrected by a later entry (OQ-2, Phase 6, Phase 7).

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

`_validate_metrics.py` Dim 4 is `rule_tag` — *"every rule tag in closed enum"* — with **weight 0.20** and **pass threshold 1.0** (*"rule_tag is mechanical (any invalid tag is …)"*), checked against `ENUM_FIELDS["rule_tag"]`. **A rule carrying any label outside the enum fails Dim 4 outright and costs up to 0.20 of the composite**, against the Phase 6.2 ship/cancel/fix human gate that fires below 0.95. This is the mechanical cost of D5's permissive arm, and it is the number to argue with. (Dim 2, the citation dimension, carries F11's cost: seeded canonical text is itself a citation.)

#### The checkout

**F8 — Concurrency.** Other sessions build in this checkout, and **plan numbers are allocated with no coordination between them**: each session takes the next free number from what it can see, and what it can see goes stale while it drafts. This is neither hypothetical nor rare — **this file's own number was taken and re-taken more than once inside the single session that produced it**, and the neighbouring sessions' files moved repeatedly over the same stretch, at one point leaving the same plan title sitting at two numbers at once, a rename caught mid-flight. A rename moves a file and never the sentences inside it, so **a document that cites another plan by number alone is citing a value that drifts** — where the citation matters, name the work, not the digits. Before touching any ledger, re-read `git status`, read the ledger live, and **commit by explicit path, never `git add -A`.** Do not touch a plan file this session did not create, for any reason: ownership is established from `git status` and from which sessions are active, never from a plan's number.

### Re-check (2026-09-24)

On 2026-09-24 this plan was re-checked against the live tree at HEAD `f251e6d` (`src/constitution.md` last changed in `6a786b3`, 2026-09-19; `src/devforge/lib/_constitute/` last changed in `22162eb`, 2026-08-28). ⚠ Line digits below are 2026-09-24 values — grep the quoted text, never the digits. **Held:** F1's seven `Section 3.5` sites and `src/CLAUDE.md`'s catalog clause; F2's table and every quoted spec string; F3's four inputs, the presence guard (grep `leaving as-is`), the snapshot block (grep `.devforge/template/.claude/agents`) and the 27 `add_parser(` calls, counted live; F4's keying (grep `"tag_or_label": heading` and `r.get("tag", "")`); F5's wiring (`install.sh`'s drift-check call in the `leaving as-is` branch, `update.sh`'s `forge_check_constitution_drift` call) and its five verify tests; F6's override footer (grep `'add rule <number>`); F7's Dim 4 weight 0.20 and threshold 1.0. **F4 is now reproduced, not only read:** a best-possible consumer state built through the real CLI — `reset`, then `add-section` + `add-rule --tag universal --text <canonical body>` for §3.x and §6.x and `add-pattern-rule --scope universal` for §4.x, every canonical body verbatim, every section at its canonical number and heading — gives `forge-internal:verify-universal-defaults` **exit 2, 32 findings, all MISSING, 0 DRIFT, all eleven sections**. 32 is today's canonical rule count as the comparator splits it: 1+9+1+1 for §3.5–§3.8, 5+5+6 for §4.1–§4.3, 1 each for §6.1–§6.4 — counted against canon `6a786b3`, and re-counted live whenever it is quoted. That state is a scratch reproduction, not a consumer. Three facts the 2026-09-20 draft did not have follow; after them, every in-place correction they forced.

#### F9 — the canonical parser swallows `## 4.` into §3.8

Reproduced 2026-09-24 on a scratch state built through the real CLI (not a consumer); the parser was read in the tree the same day.

- **The boundary regex only knows `N.N` headings.** `_universal.py`'s `_parse_universal_blocks` compiles `heading_re = re.compile(r"^(#{2,})\s+([\d]+\.[\d]+(?:\.[\d]+)*)\s+(.*)")` (grep `[\d]+\.[\d]+(?:\.[\d]+)*`). A heading numbered `N.` — `## 4. Patterns & Anti-Patterns` — never matches, so it is never a section boundary.
- **So §3.8's canonical body runs past its end.** `_parse_universal_blocks` returns a §3.8 body ending `…is not among these findings.\n\n---\n\n## 4. Patterns & Anti-Patterns`. §3.8 is the only universal sub-section in `src/constitution.md` followed by an H2; every other one is followed by a `###` heading, which the regex does match.
- **(a) Seeding from this parser breaks `verify`.** Seeding §3.8 from this parser — what every current test fixture that seeds §3.8 does, and the obvious D3(a) implementation — injects a second `## 4.` H2 into the render. On a scratch state seeded with all eleven canonical bodies, `constitute_helper render` exits 0 but `constitute_helper verify` exits 2: *"round-trip identity: section count mismatch: rendered=7, expected=6"*. A control state built with the same setters and no universal text gives `verify: ok`. **So `/devforge:constitute`'s verify step would fail on exactly the state this plan intends to create.**
- **(b) A third independent cause of non-green.** Once F4's keying is fixed, a correctly composed §3.8 — one without the swallowed H2 — reports `DRIFT` forever against this canonical body. That is a third cause beside F4's keying and the F2 filter F4 records (`_universal.py`'s `tag != "universal"` check and its `_UNIVERSAL_SECTIONS` membership check).
- **(c) The tests pass on it.** `test_verify_universal_defaults_passes_with_38_in_sync` copies the swallowed text into both sides and passes; `TestParseUniversalBlocks` asserts nothing about §3.8's tail.
- **Reach.** `_parse_universal_blocks` is called only by `_cmds_quality.py` (the comparator); `constitute_helper.py` re-exports it, and `tests/lib/test_constitute_helper.py` uses it. Its other mentions are in plan files.

#### F10 — `render` cannot carry canonical universal text

Reproduced 2026-09-24 on a scratch state built through the real CLI (not a consumer); the render code was read in the tree the same day.

- **Render's rule shape is one line.** `_render.py`'s `_render_section_body` emits `### <number> <title> [<tag>]`, an optional description, tables, then ONE line per rule — `- [<rule.tag>] <rule.text>` (its docstring; grep that string) — then code examples. `_render_pattern_bucket` does the same for §4's buckets.
- **Canonical universal sections are not one-line rules.** They are prose: bold-lead paragraphs, a fenced code block (§3.5), bold block headers with nested bullet lists (§3.6), `*Backed by*` paragraphs.
- **What the render produced** from a state seeded with the canonical bodies at the canonical parser's granularity:
  - §3.6's rules render as `- [universal] a class/module/function has one reason to change…` — **the principle NAMES (Single Responsibility, Open/Closed, …, DRY, KISS, Narrowing, Two-hats) are GONE**, because the canonical splitter puts the name in the comparison key (`tag_or_label`) and the rule schema has no field to hold it.
  - DRY, KISS, Narrowing and Two-hats render as `- [universal] - If the same logic…` — a bullet whose text starts with a bullet.
  - §3.5 renders as a single bullet carrying roughly 3.7K characters, its code fence included.
- **Consequence.** Phase 8 anchor 1's drafted check — that the rendered bodies match the canonical file — was unreachable with today's render, and **no phase owned render's shape**: D5's blast radius named render only as *"whether a label appears in the rendered constitution, and how"*. The chain table now carries render as its own link, D3 carries option (d) and a render change for (a)–(c), and Phase 3 owns the render change.

#### F11 — seeded canonical text is itself a `validate` citation

Reproduced 2026-09-24 on a scratch state built through the real CLI (not a consumer).

- `constitute_helper validate` on the seeded scratch state reports *"citation unresolved: 'plan.md'"*, with a Dim 2 citation score of 0.5 on that state. Dim 2 carries **weight 0.25** and a per-dimension threshold of **0.95**, and the composite gate is **0.95** (`_validate_metrics.py` — `_VALIDATE_WEIGHTS`, `_DIM_PASS_THRESHOLDS`, `_COMPOSITE_PASS_THRESHOLD`).
- The token comes from canonical §6.1 Minimal Changes: a grep for `plan.md` in `src/constitution.md` returns only the §6.1 line. The control state without universal text scores citation 1.0.
- Dim 2 collects its texts from the state (`_collect_citation_texts(state)`), so any seeding route that puts canonical text into the state carries this token into `validate`.
- **The cost on a real consumer depends on how many other citations it has — not measured.** 0.5 is the scratch state's number only.
- Related: `80-CONSTITUTE-CITATION-FALSE-POSITIVE-PLAN.md` owns citation false positives — another session's untracked file, cited here and never touched. `src/constitution.md` stays unedited (Tripwires), so the answer to F11 cannot be removing the token from the canon.

#### Corrected in place on 2026-09-24

Each item below was a false or incomplete sentence corrected where it stood; no D-item or OQ-item was decided, and every counter-argument survives.

- **Status line** — points to this section.
- **Evidence-class sentences** (status banner, `## Origin & evidence`, `## Phase 0 close record`, Phase 7 Verify, `## Honest bounds`, `## Context for next session`, `## When resuming work` step 10) — F4, F9, F10, F11 reproduced on a scratch state; F2, F3 found by reading; nothing measured on any consumer.
- **The governing sentence** (top and `## Context for next session`) — names the render link.
- **F1's structural bullet** — the render walk re-anchored from `_cmds_render.py`'s `section_bucket_keys` (that list is `cmd_verify`'s "Check 2: Section arrays") to `_render.py`'s `_render_constitution`.
- **F4** — reproduction noted; "fixing one cause alone" now names three causes (F4's keying, the F2 filter, F9's boundary).
- **F5** — claim sites named per plan (plan file vs released `CHANGELOG.md` section); fifth candidate `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md` D7; the `README.md` sentence and two false comments added.
- **F7** — one-clause cross-reference to F11.
- **The chain table** — new link 4 (render, F10); the detector row gains F9; later links renumbered; the "Link 1 alone is a trap" paragraph now says link 5 and qualifies its DRIFT prediction by F4 — as does item 2 of `## Context for next session`'s reverted-session record.
- **D2** — (a)'s blast radius corrected (no update path; a tracked file); option (d) added; RECOMMEND (a) re-opened, with a drafting-time lean to (d) and (d)'s counter-argument.
- **D3** — option (d) added with its record; a render change stated for (a)–(c); an F11 bullet; RECOMMEND (a) re-opened and NOT flipped.
- **D4, D5, D6** — one D3(d) cross-reference each; D5's blast radius: render bullet expanded, pre-change-state obligation added.
- **OQ-1** — the "cannot be written before D5 and D3" note limited to the exit-0 test; the before-fix measurement is runnable today.
- **OQ-2** — claim sites named; 2026-09-24 baseline recorded; amendments go to plan files only; fifth candidate recorded, not reopened.
- **OQ-3** — D2(d) named beside D2(a).
- **Phase 2** — heading gains F9; scope: F9's section boundary, D5's pre-change-state obligation, and the drift-check comment + remediation line; Verify: the §3.8 body test and the render exception.
- **Phase 3** — heading gains render, F10 and F11; scope: (a)'s update gap, D2(d), D3(d), the render change (F10); Verify: round-trip `verify`, §3.6 names, `validate` citations (F11), and "the first time any real-producer state has been fed to that verb" corrected.
- **Phase 5** — sixth hand-authored fixture `test_render_from_seeded_state_includes_design_fidelity`; the grep's five hits; F9 seeding note.
- **Phase 6** — sites precise; released `CHANGELOG.md` sections never edited; baseline re-run at build time; grep extended; `108-…` recorded.
- **Phase 7** — `README.md` becomes an EDIT; the `update.sh` comment; the `## [Unreleased]` entry carries any released-claim correction.
- **Phase 8** — anchor 1 rewritten per D3; anchor 5 pinned to after-fix, anchor 5b added; failure mapping gains F9 and F10.
- **Honest bounds** — evidence; the "no migration owed" bullet refined; `108-…`; a bound on F11's cost.
- **Tripwires, Non-goals, Trap 5** — enumerations gain `108-…`; released `CHANGELOG.md` sections never edited; the 32-rule count joins the counted-live list; Phase 7's `update.sh` comment named as a comment; D3(d)'s §4.x exclusion tied to the §4.1–§4.3 tripwire.
- **Routing** (Tripwires bullet, Phase 2 and Phase 3 route lines, `## When resuming work` step 6) — "Python is confined" became "Code is confined", naming every non-Python code edit (drift-check shell lines, `install.sh` / `update.sh` lines, `src/manifest.json` entry) with exactly one route: python-engineer → python-reviewer plus a scratch-target install/update run; markdown and Phase 7's single `update.sh` comment go instruction-author → instruction-reviewer.
- **Traps** — Trap 11 added.
- **File anchors** — `_cmds_render.py` re-described; `_render.py`, `src/manifest.json`, `README.md`, `CHANGELOG.md` and the other anchors D2 and F5 need added; tests line extended.
- **When resuming work** — step 3 re-verifies F1–F11 with new grep strings; step 10's evidence class.

---

## The chain, link by link

| Link | What should happen | What happens today | Fact |
|---|---|---|---|
| 1. The spec names the sub-sections | The model is told the canonical numbers and headings | Six of eight universal numbers are wrong or absent; the range cannot hold the canon | F2 |
| 2. Something supplies the body text | The canonical prose reaches the run | No input carries it; the root copy is presence-guarded, uninstructed and overwritten by render | F3 |
| 3. The state records them | `add-rule` stores a rule with an identity | `--tag` is the only identity and it is a four-value enum | F4, F6 |
| 4. The render reproduces them | The rendered constitution carries the canonical text, names included | One `- [<tag>] <text>` line per rule: names lost, nested lists doubled, prose and code fence collapsed into one bullet | F10 |
| 5. The detector compares | An in-sync consumer returns exit 0 | Heading vs enum value — every universal section reports MISSING; the canonical parser also swallows `## 4.` into §3.8 | F4, F9 |
| 6. The tests hold the line | A real-producer in-sync fixture proves exit 0 | All five verify tests use hand-authored or empty state; the real-producer fixture never reaches the comparator | F4, F5 |

**Link 1 alone is a trap.** Fixing F2 without F3 changes the failure mode rather than removing it: with correct numbers and no body-text source, the model produces the canonical heading at the canonical number and **invents** the body. That is quieter than today's absence, not louder — and once F4's keying is repaired, link 5 would then report `DRIFT` instead of `MISSING`, which reads like a smaller problem. (Until then link 5 reports `MISSING` whatever the body says, because the key never matches — for verbatim canonical bodies this was reproduced on 2026-09-24.) **This is the whole argument for treating delivery as inseparable from numbering.**

---

## Decisions to ratify

**Nothing below is ratified.** **(Drafting-time text, kept as drafted — Phase 0 CLOSED 2026-09-24; D1–D7 and OQ-1–OQ-3 ratified as recommended, D2 → (d) and D3 → (a) by the orchestrator's reading of their re-opened standing text; see `## Phase 0 close record`.)** Each item states the decision, the options, a recommendation and the strongest counter-argument, **recorded rather than answered away**. Proposed emitted wording is **substance, not final text**: the builder may reword, but every element named must survive. **No emitted sentence may name plan vocabulary ("D5", "plan NN", "Phase 0", "F4").**

### D1 — Scope: does this plan include the label fix, or only the mechanism?

F1 (the "Section 3.5" label collision) and F2–F4 (the universal-sections chain) are two problems that share a number and nothing else. F1 is a text-honesty fix on a block that works correctly; F2–F4 are a broken mechanism.

- **(a) Both, in one plan.** One ratification, one docs sweep, one consumer run.
- **(b) Mechanism only**; F1 goes to its own plan or a standalone fix.

- **RECOMMEND (a)**, with this recorded: **the label fix is independently shippable.** It depends on no other decision here, blocks nothing, and is not blocked by anything — its phase carries an explicit "may ship alone" note so a later session is never forced to drag the mechanism work along to land it. It rides here because it is the one part of this subject a user has actually met, and splitting it would leave the only observed item ownerless.

**Counter-argument, recorded:** bundling an observed one-line-class fix with an unobserved four-fact mechanism rebuild means the observed fix waits for the unobserved one to ratify. If Phase 0 stalls, the user-visible confusion stays in the tree — which is exactly why the "may ship alone" note is part of the recommendation and not a nicety.

### D2 — Source of canonical text

Nothing supplies §3.5–§3.8 and §6.1–§6.4 body text to a `/devforge:constitute` run (F3). Something must.

- **(a) A snapshot at `.devforge/template/constitution.md`** — one added line in `install.sh`'s existing snapshot block (`:432-434`). ⚠ **That line must copy from `$TEMPLATE_DIR/src/constitution.md` directly** — `install.sh:365`'s pattern, **not** the block's own two lines' pattern: `:433-434` both copy from `$TARGET_DIR`, and `$TARGET_DIR/constitution.md` holds the shipped template only on the branch where `:365` ran. On a brownfield reinstall the presence guard at `:364` takes its `else` branch (`:366-372` — OQ-3's), `:365` never runs, and that path holds whatever the consumer already had, most likely a previously **rendered** constitution. **Sourcing from `$TARGET_DIR` would break this option's own guarantee on exactly the installs where it matters.** Sourced from `$TEMPLATE_DIR`, the run reads a path that is by construction the shipped template and never a rendered artifact, whichever branch the guard took.
  - ⚠ **(a) has no update path** (read 2026-09-24). `update.sh` refreshes `.devforge/template/` only through `src/manifest.json`'s `templateDerived.mappings`, which holds exactly two entries — `generated:agents` → `.claude/agents` and `generated:coreLLM` → `CLAUDE.md` — and it three-way-MERGES against that snapshot. `constitution.md` sits in `projectOwned` (*"NEVER overwrite"*), and no line of `update.sh` copies or merges it: its `constitution` mentions are the drift check's source line, its call and comment, and the false comment F5 records. **So under (a) as written the snapshot freezes at install-time canon:** after a canon amendment, a `/devforge:constitute` re-run seeds STALE text, and the drift check — which reads the TEMPLATE's `src/constitution.md` — keeps reporting it. Adding the file to `templateDerived` would make it a three-way-merge baseline, which is the wrong semantics for text that must be replaced, not merged.
  - ⚠ **(a) adds a tracked file to every consumer repo.** `.devforge/template/` (SINGULAR) stays TRACKED in consumers — `src/devforge/storage-rules.md` records it as the agent three-way-merge baseline.
- **(b) Inline the canonical prose into the spec** — the text lives in `constitute/main.md` or a reference file, and the model composes from what it reads.
- **(c) Another route** — a helper verb that emits the canonical blocks on stdout (which collapses into D3), or reading `src/constitution.md` from the installed template directory directly.
- **(d) A `templateOwned` mapping** *(added 2026-09-24)* — one entry in `src/manifest.json`'s `templateOwned.files[]` mapping `src/constitution.md` to a gitignored CODE-class target, e.g. under `.devforge/lib/` or `.devforge/templates/` (both listed in `src/files/devforge.gitignore`). `templateOwned` already ships single files generically on every update, with overwrite semantics — precedent: `{ "source": "src/devforge/storage-rules.md", "target": ".devforge/storage-rules.md" }` — and `update.sh`'s `expand_templateOwned_pairs` expands every entry. So the canon stays single-sourced in `src/constitution.md`, is refreshed on every update with no new `update.sh` logic, and stays version-locked with the helper that parses it — which matters because of F9: the parser and the text it parses ship together.
  - **Costs, recorded:** `install.sh` needs whatever line its own pattern requires (verify at build — not verified in the 2026-09-24 re-check); `src/devforge/storage-rules.md`'s class list gains an entry; and ⚠ **a markdown data file inside a CODE-class path is a mild invention** — the nearest precedents are `_design/js/*.js` (non-Python assets inside a lib sub-package) and `.devforge/command-refs/` (markdown in a CODE-class path, but instruction text the model reads, not data a helper parses). Flagged, not hidden.

- **RECOMMEND — RE-OPENED 2026-09-24.** The drafting-time recommendation was **(a)**, conditionally and subject to re-derivation after D5, on three stated grounds: it adds one line to a block that already exists and already solves exactly this problem for agents and `CLAUDE.md`; it puts the text where an update ships it; and it keeps the canonical prose single-sourced in `src/constitution.md`. **The second ground is false** — (a) has no update path (above) — so (a)'s recommendation no longer stands on its own stated reasoning.
- **Drafting-time view after the re-check: leans to (d)**, still **conditional on D5 and on D3**. (d) keeps (a)'s cheapness (one manifest entry plus whatever `install.sh` needs, no new `update.sh` logic) and its single source, and it is the only option whose text an update refreshes. Nothing is decided here.
- **Counter-argument to (d), recorded:** it puts a markdown file that a helper parses as data inside a CODE-class path — a first of its kind; it adds one more manifest entry and a `storage-rules.md` edit; and it ships a second on-disk copy of the canon to every consumer, where (a) reused a mechanism whose whole purpose is recording what the template shipped.
- ⚠ **Sequencing note, load-bearing: D2 is decided AFTER D5.** If D5 gives a rule an identity separate from its tag, the snapshot's required shape changes — a flat markdown copy may no longer be enough, and a structured emission (the (c) family) may become the cheaper carrier. **A ratifier who takes D2 before D5 has decided the carrier before knowing what it must carry.**

**Counter-argument, recorded:** (b) is the only option that needs no install-time change at all, and inlining reads as the simplest thing. It is not: `verify-universal-defaults` compares body text byte-for-byte after normalization, so inlined prose becomes **byte-critical duplication** — two copies of the same paragraphs that must never diverge, with the detector turning any divergence into a `DRIFT` finding on every consumer. That is the drift class this plan exists to close, reintroduced at a new site. Recorded and not answered away: (a) still leaves two copies on disk in a consumer (the snapshot and the render), but only one is ever read as a source — and (d) leaves the same two, its CODE-class copy in the snapshot's place.

### D3 — Who seeds the universal sections

Given a text source (D2), something must put those sections into `.devforge/constitute.json`.

- **(a) A new `seed-universal` verb** — the helper reads the canonical source and writes all eleven sections itself. Helper-owns-shape: the numbers, headings, tags and rule identities are the helper's, and the model composes nothing.
- **(b) Extend `reset`** — a freshly reset state already carries the universal sections. One fewer verb; every `reset` call in every test changes shape.
- **(c) The model follows an instruction** — the spec tells it to read the source and issue `add-section` / `add-rule` per universal sub-section.
- **(d) Render-from-source** *(added 2026-09-24)* — `render` emits the universal sub-sections verbatim from the canonical text carrier (D2), and the state records only that they are present (e.g. which canonical version was rendered), not their text. Recorded as found, without a verdict:
  - **The comparator could parse the consumer's rendered `constitution.md` with the same parser as the canonical side**, so both sides key identically by construction and **D5's identity field is not needed for comparison** — for §3.5–§3.8 and §6.1–§6.4. ⚠ Not for §4.1–§4.3: render prints those buckets as `### Always Do (Universal)`, `### Never Do (Universal)` and `### Prefer (Universal)`, with no `4.x` number (`_render.py`'s `_render_constitution` and `_render_pattern_bucket`, read 2026-09-24), so a number-keyed parser would not find them in a rendered file; their comparison stays on the state side.
  - **D6's overrides of universal rules would have no state home** — effectively D6(b).
  - **`render` gains a second input besides the state**, which bends the helper-owns-shape statement that render walks the state — the render contract F2 quotes (*"render artifact rebuilt from `.devforge/constitute.json`"*; *"walks the locked schema"*) would change with it.
  - F11 would not arise under (d) as reproduced: Dim 2 reads citation text from the state (`_collect_citation_texts(state)`), under (d) the state holds no §3.5–§3.8 or §6.1–§6.4 text, and the one unresolved token F11 found comes from §6.1. How `validate`'s Dim 1 slot-fill scores a state that records universal sub-sections by presence only is unexamined.
  - ⚠ **Applying (d) to §4.1–§4.3 would change their `add-pattern-rule` production path, which this plan's Tripwires and Non-goals forbid** — so (d) as drafted covers §3.5–§3.8 and §6.1–§6.4 only, and §4.x stays on its path.

- **Whichever of (a)–(c) is ratified ALSO carries a render change** (F10): a rule must be able to render as a named block — name, prose, nested list and code fence intact — not as a one-line `- [<tag>] <text>` bullet. Phase 3 owns it.
- **Whichever option is ratified, F11 is owed** (recorded 2026-09-24): a route that puts canonical text into the state carries canonical §6.1's `plan.md` token into `validate`'s Dim 2 as an unresolved citation (weight 0.25, threshold 0.95, composite gate 0.95). Phase 3 must show `validate` reports no unresolved citation originating in canonical text, or state each one with its Dim 2 cost.

- **RECOMMEND (a)**, **conditional on D5** — it becomes largely mechanical once D5 settles what a rule's identity is.
  - (c) is the option this plan exists to retire: it is what happens today, minus the text source, and it puts eleven exactly-specified sections back in the hands of the composer. Helper-owns-shape says the helper owns structure and the LLM composes values; canonical universal text has no values to compose.
  - (b) changes the meaning of `reset` from "empty state" to "state with content", which every existing test and every re-run assumes.
- ⚠ **RE-OPENED 2026-09-24.** The recommendation of (a) was made without (d) on the table and without knowing that render cannot carry the text (a) would seed (F10). **Drafting-time view: (d) must be argued against (a) at Phase 0.** The recommendation is **not** flipped here — it stays (a), re-opened. **(2026-09-24 close: (d) was not argued — the blanket directive ratified the standing (a), and (d) stays live for re-opening; see `## Phase 0 close record`.)**

**Counter-argument, recorded:** (a) adds a 28th verb to a helper that already has 27, and the framework has a standing preference for extending one binary over adding another composer. Accepted as a cost, not refuted: the alternative that avoids the verb is (b), whose price is redefining `reset`. **Recorded 2026-09-24:** (a) now also needs a render change (F10) on top of D5's schema change and the new verb; (d) trades all three for a render change of its own plus a presence record in the state, and needs no rule identity for the eight sections it covers.

**Counter-argument to (d), recorded:** it bends the render contract (a second input besides the state), leaves user overrides of universal rules nowhere to live, and splits the comparator into two paths — parser-against-parser for eight sections, state-against-parser for §4.1–§4.3 — so the universal set is no longer compared one way.

### D4 — What keys a rule during comparison

`tag_or_label` currently means two different things on the two sides (F4): a heading (or bold sub-label) on the canonical side, an enum tag on the consumer side. The comparator dictionaries are built from it.

- **(a) Compare on a new identity field** that both sides populate with the same string (depends on D5 giving a rule such a field).
- **(b) Compare on the section `heading`**, which `_universal.py` already carries in the return shape and `_cmds_quality.py` already ignores — comparing whole-section bodies rather than per-rule ones for the default branch.
- **(c) Compare positionally** — rule *i* against rule *i* within a section.
- **(d) Keep `tag_or_label` and make the consumer side emit the same thing the canonical side does** (which collapses into D5).

- **RECOMMEND (a)**, **conditional on D5** — once a rule carries an identity separate from its tag, the comparator keys on it and the two sides mean the same thing by construction.
- **Recorded about (c):** positional comparison is the only option that needs neither a schema change nor a new field, and it is the one that fails silently — a consumer who legitimately appends one project rule to a universal section shifts every later index and the detector reports drift on rules nobody touched.
- **Recorded about (b):** it is strictly cheaper than (a) and strictly weaker. It would make §3.5, §3.7, §3.8 and §6.1–§6.4 comparable today with zero schema change, and it would leave §3.6 and §4.1–§4.3 — the sections whose canonical keys are bold sub-labels — exactly as broken as they are now.
- **Recorded 2026-09-24:** D3(d) would let the comparator run one parser over both the canonical file and the consumer's rendered `constitution.md` for §3.5–§3.8 and §6.1–§6.4, keying both sides identically by construction — a keying answer none of (a)–(d) here names. §4.1–§4.3 would stay on whatever this decision ratifies (D3(d)'s record). Whichever keying is ratified, F9's section boundary must be fixed first, or §3.8 never compares equal.

**Counter-argument, recorded:** (a) is the most invasive option in a plan whose cheapest correct option is (b), and it is recommended partly because there are no production installs to protect (see `## Honest bounds`). If that ever stops being true, (b) becomes the proportionate answer for the sections it covers, and §3.6 / §4.x stay uncovered — which is a real, statable partial fix, not a failure.

### D5 — Does `add-rule` accept a label outside the `rule_tag` enum?

⚠ **This decision governs the rest. Once it is settled whether a rule carries an identity separate from its tag, D3 and D4 become largely mechanical.** Decide it first.

⚠ **Recorded 2026-09-24:** D3(d) would make this decision's identity field unnecessary for comparing §3.5–§3.8 and §6.1–§6.4 (D3(d)'s record); §4.1–§4.3 would still need it or D4's repair. "Decide it first" stands as drafted — a ratifier weighing D3(d) records what D5 still governs under it.

- **(a) Yes — a rule gains an identity field** (a label / name) distinct from `--tag`, which stays the four-value enum it is. The canonical side's heading or bold sub-label lands there; the consumer side emits it; the comparator keys on it (D4(a)).
- **(b) No — the enum stays the only identity**, and the comparison is repaired some other way (D4(b) or (c)).

- **RECOMMEND (a).**
- **Blast radius, stated so it is argued with rather than discovered:** the `rule` schema propagates to
  - `add-rule`'s CLI surface and its `--tag` validation,
  - `validate`'s Dim 4 `rule_tag` — **weight 0.20, pass threshold 1.0** (F7), so a label smuggled into `tag` costs up to 0.20 of the composite against a 0.95 human gate,
  - `render` — whether a label appears in the rendered constitution, and how; ⚠ **and, recorded 2026-09-24 (F10), render today cannot carry multi-paragraph prose, a fenced code block or a nested list inside a rule at all** — it emits one `- [<tag>] <text>` line per rule,
  - **both** comparison sides in `_universal.py`,
  - the override grammar's `[<tag>]` token at `constitute/main.md:224-228` (F6), which is user-facing,
  - and the tests, including every fixture that constructs a rule.
- **And one obligation that is not a schema surface** (recorded 2026-09-24): **the comparator's behaviour on state constituted before the change.** The drift check always pairs the NEW helper with OLD state — `scripts/constitution-drift-check.sh`: *"The freshly-shipped TEMPLATE helper is used (not the consumer's installed helper), because update.sh runs this BEFORE it copies the new lib"*, and `update.sh` calls it before the equal-version bail. So every update of every install constituted before the change runs the new comparator on rules written by the old schema. D5 must say what the comparator reports there — e.g. one line naming re-constitution, not one MISSING per rule. This is structural, not a production-install question.

**Counter-argument, recorded:** (b) is a real position and the cheapest one. The enum exists because a rule's tag is a *classification* — where the rule came from and whether it is universal — and a name is a different kind of thing that the schema deliberately did not carry. Adding one widens a locked schema across seven surfaces to serve a comparator that (b) could repair in one file. The case for (a) is that F4's root cause **is** the absence of an identity: the comparator did not invent the mismatch, it inherited a schema in which a rule has no name to compare.

### D6 — Fate of user overrides over universal rules

Today the per-section echo offers `add rule` / `drop rule` / `replace rule` / `drop section` against every section, universal ones included (F6). Once universal sections are seeded by the helper with canonical text (D2, D3), a user override against one of them is a deliberate divergence — and the detector will report it as `DRIFT` on the next update, forever.

- **(a) Overrides stay available against universal sections**, and the resulting drift finding is accepted and named as such in the echo.
- **(b) The override grammar is withheld for universal sections** — the echo offers them for project-specific sections only, and a universal section is presented as law.
- **(c) Overrides stay available, and an overridden universal rule is recorded** so the detector can tell a deliberate override from stale text.

- **RECOMMEND (a)** — with the echo saying plainly that an override of a universal rule will be reported as drift on every update until it is reverted.
- **Why not (b):** it removes a capability a user has today, on a plan with no evidence anyone misused it, and it makes `drop section` mean different things in different sections of the same echo.
- **Why not (c):** it is the correct answer and the expensive one — a per-rule override record is a second schema change on top of D5's, with its own comparison semantics. **Recorded as the named strengthening arm, with an observable trigger: a user who reverts an intentional override because the drift warning kept naming it.**
- **Recorded 2026-09-24:** under D3(d) the state holds no universal text, so an override of a universal rule has no state home — D3(d) makes this decision effectively (b) for the sections it covers. This decision is read against whatever D3 ratifies. **(Moot — D3(d) not taken (2026-09-24 close); D3(a) keeps universal text in the state, so D6(a)'s overrides keep a state home.)**

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
- ⚠ **Note for whoever ratifies:** the exit-0 in-sync test cannot be written before D5 and D3 are built. A real-producer in-sync fixture that returns exit 0 requires a route by which canonical text and identities enter the state through the real CLI — or, under D3(d), reach the rendered file. That is a phase ordering constraint, not an argument against. **Qualified 2026-09-24:** the before-fix measurement needs no such route. The real CLI already stores canonical body text through `add-rule --tag universal --text` and `add-pattern-rule --scope universal`, and that state was built and measured on 2026-09-24 (`### Re-check (2026-09-24)`: exit 2, 32 MISSING, 0 DRIFT).

### OQ-2 — Are the plans 86 / 89 / 99 "designed drift" claims artifacts?

Plans 86, 89 and 99 each tell consumers to expect a `verify-universal-defaults` DRIFT/MISSING finding as designed consequence of a constitution amendment, at the sites F5 names: `86-FOWLER-REFACTORING-GAPS-PLAN.md`'s claim only in `CHANGELOG.md` under `## [2.0.10]`; `89-TEST-FOUNDATION-HARDENING-PLAN.md`'s in its plan file and under `## [2.0.10]`; `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md`'s in its plan file and under `## [2.0.12]`. **Under F4 those findings would appear whether or not anything drifted.**

- **RECOMMEND: establish it by a run, not by reading, and record the result in this plan's own build record.** The run is: a real-producer in-sync consumer state (OQ-1's fixture) against the current canonical file, **before** the comparison fix and **after** it. Before-fix exit 2 with every universal section MISSING, after-fix exit 0, is the finding.
- **Before-half baseline, recorded 2026-09-24 (canon at `6a786b3`):** exit 2, 32 findings, all MISSING, 0 DRIFT, all eleven sections — on a scratch state built through the real CLI with every canonical body verbatim (`### Re-check (2026-09-24)`). The before half is therefore runnable today; only the after half needs Phases 2–3. ⚠ **Phase 6 re-runs the before half at build time** — the canon may change before then, and this number is a baseline, not the result.
- **If established true:** **dated amendments**, never rewrites, at the **plan files** that carry a claim — `89-TEST-FOUNDATION-HARDENING-PLAN.md` and `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md` — the claim stays on the record, with a dated note saying the finding it predicted was not distinguishable from an artifact of the comparator. `44-CONSTITUTION-DRIFT-WIRING-PLAN.md`'s *"~30 MISSING"* / *"29 MISSING findings"* records are a **fourth** candidate (F5) and take the same treatment. `86-FOWLER-REFACTORING-GAPS-PLAN.md` carries no claim in its plan file and gets no amendment. **Released `CHANGELOG.md` sections are never edited:** the `## [2.0.10]` claims (86's and 89's) and the `## [2.0.12]` claim (99's) are corrected only by Phase 7's `## [Unreleased]` entry.
- **Fifth candidate, recorded and NOT reopened:** `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`'s ratified D7 rests partly on the cost of a fourth drift finding (F5). OQ-2 records, in this plan, whether that cost premise held; the decision stays that plan's, and that plan file is not amended.
- **If established false or indistinguishable:** record that, and amend nothing.
- ⚠ **This plan does not get to conclude it either way from reading.** F4 says the comparator cannot return green; it does not by itself say those specific consumers had no real drift. Those installs may have had both.

### OQ-3 — Does `install.sh:364`'s presence guard stay?

The guard leaves an existing root `constitution.md` alone (F3). Under D2(a) or D2(d) the canonical text would arrive by a different path (`.devforge/template/`, or D2(d)'s CODE-class target), so the guard's role changes. **(2026-09-24 close: D2(d) is ratified; D2(a) is not taken — its mentions below are drafting-time text.)**

- **RECOMMEND: it stays, untouched.** Its job is brownfield safety — never overwrite a user's constitution — and that job is unchanged by anything here. D2(a) or D2(d) makes it irrelevant to the text source rather than wrong.
- **Alternative:** drop the root copy entirely, since after D2(a) or D2(d) nothing reads it as a source and `render` overwrites it anyway. That is a real simplification and it is **out of this plan's scope**: the root copy is what a freshly installed, never-constituted project has as its constitution, and removing it is a separate decision with its own blast radius.
- **Recorded either way:** `install.sh:371`'s drift-check call sits in the guard's `else` branch, so anything done to the guard touches when the drift check runs.

---

## Phase 0 close record

**CLOSED 2026-09-24.** **D1–D7 and OQ-1–OQ-3 are ratified as recommended — D2 and D3 by a reading of their re-opened standing text, marked in the Outcomes table.** Nothing was amended, nothing was declined, no item is left open, and **build phases MAY start.** ⚠ **Nothing is built.** *(True at the close. Added 2026-09-25 at build: Phases 1–6 are now BUILT — each phase's build record under `## Phases`.)*

Every statement in this record is dated 2026-09-24 unless it names another date.

**What this record was required to contain** — the drafting-time list, kept as drafted (its opening line then read *"**Pending.** Nothing is ratified. No build phase may start until this section carries an outcome — ratified, amended or declined — for every one of D1–D7 and OQ-1–OQ-3."*; that is the pre-close state, quoted as history). When it closes it must state, following the house pattern:

- **Each** of D1–D7 and OQ-1–OQ-3 by name, with its outcome. **No item silently omitted** — check by NAME, never against a range (plan 100's Phase-4 tripwire: a range reads as complete while the enumeration beside it drops a member).
- Whether **per-item deliberation was supplied**, and whether the close was an **explicit pick or a delegation**.
- That **every decision keeps its counter-argument** — a ratified decision with its counter-argument deleted cannot be re-opened honestly.
- **Which files each outcome puts in scope**, per phase.
- ⚠ That **ratification changes no evidence class**: F1 observed once; F4, F9, F10 and F11 reproduced on 2026-09-24 on a scratch state built through the real CLI (reproductions, not consumer incidents); F2 and F3 found by reading; nothing measured on any consumer.

⚠ **D5 must be answered before D2, D3 and D4 are read as settled.** If the close is a blanket ratification, it still records that ordering, because D2's, D3's and D4's recommendations are each explicitly conditional and a blanket close does not discharge a condition.

**It contains each of them:** every one of D1–D7 and OQ-1–OQ-3 by name, in the Outcomes table; whether deliberation was supplied and whether the close was a pick or a delegation, under **How it closed**; that every decision keeps its counter-argument, same block; the files each outcome puts in scope, per phase, under **What the outcomes put in scope**; the evidence class, under **How it closed**; and the D5-first ordering with each condition discharged explicitly, under **Ordering and conditions**.

**How it closed — 2026-09-24.**

- A **single blanket maintainer directive**, given in the maintainer's own words, in Ukrainian. English paraphrase: *"commit. 0 ratified"* — the "0" is Phase 0.
- **It came one message after the orchestrator argued that D3 — (a) against (d) — should be decided before D5, or jointly with it, rather than D5 first. The directive did NOT adopt that argument.** It is recorded here as **the orchestrator's argument, not ratified**, and it stays live for re-opening (**What this record does NOT close**).
- **No per-item deliberation was supplied, and this record says so.** The precedent is `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`'s close record, which states the same.
- **It is a PICK, not a delegation** (`98-DELEGATED-REPLY-ATTRIBUTION-PLAN.md`'s D1 distinction): it states an outcome rather than handing the decision back. ⚠ **But it names no option per item.** The outcomes below are **this plan's own recommendations, taken under a blanket approval — not ten separate maintainer choices**, and no sentence here may be read as the maintainer having weighed any individual counter-argument. **Two items, D2 and D3, carried re-opened text on the day of the close; what "as recommended" means for them is the orchestrator's reading**, marked as such in their rows.
- **Every decision keeps its counter-argument.** Nothing under `## Decisions to ratify` is deleted, shortened or answered away by this close, because **a ratified decision with its counter-argument deleted cannot be re-opened honestly.** That section's drafting-time lead-in keeps its opening sentence, *"Nothing below is ratified."*, with a dated parenthetical beside it naming this close. **Arms not taken are LABELLED "not taken (2026-09-24 close)", never deleted** — in Phase 2, Phase 3, Phase 8 anchor 1, D6 and OQ-3.
- ⚠ **Ratification changes no evidence class**, and this close changed none: F1 observed once; F4, F9, F10 and F11 reproduced on 2026-09-24 on a scratch state built through the real CLI (reproductions, not consumer incidents); F2 and F3 found by reading; nothing measured on any consumer. A blanket approval of a reading is still a reading.

### Outcomes — 2026-09-24

| Item | Outcome (2026-09-24) | What it settles |
|---|---|---|
| **D1** | Ratified as recommended | **(a) Both, in one plan.** F1's label fix rides with the mechanism work, and **Phase 1 may ship alone.** |
| **D2** | **Ratified — (d), by the orchestrator's reading of re-opened text** | ⚠ **One of two rows that are not a plain blanket "as recommended".** D2's standing text is *"RECOMMEND — RE-OPENED 2026-09-24"* followed by *"Drafting-time view after the re-check: leans to (d), still conditional on D5 and on D3"*. **No other standing recommendation exists, so the lean is what the blanket ratified** — **(d), one `templateOwned.files[]` entry in `src/manifest.json` mapping `src/constitution.md` to a gitignored CODE-class target.** ⚠ **This is the orchestrator's reading of the text under the blanket, not a maintainer pick of (d); the maintainer may re-open it.** (a), (b) and (c) are **not taken (2026-09-24 close)**; the counter-argument to (d) and the counter-argument about (b) stay live. |
| **D3** | **Ratified — (a), the standing RECOMMEND** | ⚠ **The other row that is not a plain blanket "as recommended".** D3's standing RECOMMEND is **(a), a new `seed-universal` verb**, RE-OPENED 2026-09-24 and explicitly NOT flipped; **the blanket ratified that standing text.** **(d) render-from-source was not deliberated**: its record and both counter-arguments (to (a) and to (d)) stay live, and so does the orchestrator's D3-before-D5 argument (**How it closed**). (a) carries F10's render change and F11's citation obligation (Phase 3). (b), (c) and (d) are **not taken (2026-09-24 close)**. |
| **D4** | Ratified as recommended | **(a) Compare on the new identity field** D5 gives a rule; both sides populate it with the same string. |
| **D5** | Ratified as recommended | **(a) A rule gains an identity field distinct from `--tag`**, and `--tag` stays the four-value `rule_tag` enum. Its blast radius and its pre-change-state obligation are Phase 2's scope; its user-facing half (F6's `[<tag>]` override grammar) is Phase 4's. |
| **D6** | Ratified as recommended | **(a) Overrides stay available against universal sections**, and the echo says plainly that an overridden universal rule is reported as drift on every update until it is reverted. (c) stays the named strengthening arm, with its trigger. |
| **D7** | Ratified as recommended | **(a) A fixed 8** — 3.5–3.8 reserved for the universal set, seeded and never composed; 3.1–3.4 stay a composed range. *"4-7"* leaves the tree. |
| **OQ-1** | Ratified as recommended | **Yes** — the `verify-universal-defaults` tests move onto the real-producer principle, as Phase 5. |
| **OQ-2** | Ratified as recommended | **Establish it by a run** — Phase 6. The before-half baseline is already recorded (32 MISSING / 0 DRIFT / exit 2 at canon `6a786b3`) and is re-run at build time. Amendments go to plan files only; `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`'s D7 is recorded, never reopened. |
| **OQ-3** | Ratified as recommended | **The presence guard stays, untouched** (grep `leaving as-is` in `install.sh`). |

**Ordering and conditions — 2026-09-24.**

- **The directive gave no order. D5 was taken as settled first, then D4, D3 and D2** — this plan's own order (the ⚠ paragraph above and D2's sequencing note).
- **D4(a) was conditional on D5** → D5(a) is ratified → **discharged.**
- **D3(a) was conditional on D5** → D5(a) is ratified → **discharged.**
- **D2's lean was conditional on D5 and on D3.** D2's sequencing note warned that under an identity field *"a flat markdown copy may no longer be enough"*. Under D3(a) the `seed-universal` verb derives each rule's identity from the canonical markdown with the parser — the section heading or bold sub-label, the same keys `_parse_universal_blocks` already produces once F9's boundary is fixed — so a flat copy suffices → **discharged.** ⚠ **This discharge reasoning is the orchestrator's, not the maintainer's.** If the build finds a rule identity the parser cannot derive from the canonical markdown, the discharge fails and D2 is re-opened, not patched.
- **D6 was to be read against D3's outcome** (its 2026-09-24 note). D3(a) keeps universal text in the state, so D6(a)'s overrides keep a state home; the D3(d) note is **moot**.

**What the outcomes put in scope — 2026-09-24.**

Each ratified item is checked here **by NAME, never against a range**, and the phase that carries it is named. Paths below were verified by grep on 2026-09-24; they drift, and `## When resuming work` step 3 re-verifies them.

- **Phase 1 — D1.** `src/commands/constitute/main.md` — the seven `Section 3.5` sites, the user-facing echo line first; `src/CLAUDE.md` — the `#### /devforge:constitute` clause.
- **Phase 2 — D5, D4, F9, and D5's pre-change-state obligation.** In `src/devforge/lib/_constitute/`:
  - `_schema.py` — the rule shape gains the identity field; the `rule_tag` enum is unchanged.
  - `_cli.py` — the `add-rule` and `add-pattern-rule` surfaces.
  - `_cmds_set.py` — `cmd_add_rule` and `cmd_add_pattern_rule`.
  - `_cmds_render.py` — `cmd_verify` also checks every rule's tag against `ENUM_FIELDS["rule_tag"]`, for section rules and for pattern-bucket rules. ⚠ **Recorded 2026-09-24: this surface is NOT in D5's blast-radius list**; it is scope here, and D5's counter-argument keeps its drafted "seven surfaces".
  - `_render.py` — how the identity renders (D5's render bullet). The full F10 render change is Phase 3's.
  - `_validate_metrics.py` — Dim 4.
  - `_universal.py` — both comparison sides; F9's section boundary.
  - `_cmds_quality.py` — the comparator keyed per D4(a), and its behaviour on state constituted before the change.
  - Outside that package: `scripts/constitution-drift-check.sh` — Check A's comment and printed `Fix: re-run …` line; `tests/lib/test_constitute_helper.py`.
- **Phase 3 — D2(d), D3(a), F10, F11, OQ-3.**
  - `src/manifest.json` — the `templateOwned` entry (D2(d)).
  - `install.sh` — the line its own pattern requires; the presence guard untouched (OQ-3).
  - `src/devforge/storage-rules.md` — the class entry (markdown — instruction lane).
  - The `seed-universal` verb (D3(a)) — `_cli.py` plus a `_cmds_*.py` module; which module is a build choice.
  - `_render.py` — F10's render change: a rule renders as a named block.
  - `src/commands/constitute/main.md` — the verb wired before Section 3's and Section 6's echoes.
  - Tests, including F11's `validate` citation check.
  - `src/files/devforge.gitignore` — only if the chosen target is not already under an ignored path; `.devforge/lib/` and `.devforge/templates/` already are.
- **Phase 4 — D7, D6, and D5's user-facing half** (F6's `[<tag>]` override grammar). `src/commands/constitute/main.md` — the Section 3 and Section 6 compose paragraphs and the echo override footer; `src/commands/constitute/references/section-shapes.md` — the Section 3 and Section 6 blocks, the *"Function Length"* example, the CBM-first anchor, and its `rule_tag` bullet if the identity field needs documenting there.
- **Phase 5 — OQ-1**, as Phase 5 lists.
- **Phase 6 — OQ-2.** Plan files `89-TEST-FOUNDATION-HARDENING-PLAN.md`, `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md` and `44-CONSTITUTION-DRIFT-WIRING-PLAN.md` only; `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md` recorded, not reopened; `86-FOWLER-REFACTORING-GAPS-PLAN.md` has no plan-file site.
- **Phase 7 — docs**, as Phase 7 lists. **Phase 8 — the user gate**, not run.
- **By name, every item has a phase:** D1 → 1; D2 → 3; D3 → 3; D4 → 2; D5 → 2 and 4; D6 → 4; D7 → 4; OQ-1 → 5; OQ-2 → 6; OQ-3 → 3. None is carried by no phase.

**Build sequencing — 2026-09-24.**

- **Phase 0 is CLOSED and build phases MAY start.** The sequencing below is the maintainer's numeric order plus this plan's own phase order — not a new gate.
- The maintainer works open root plans **in numeric order** (stated 2026-09-21, recorded in `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`'s close record, which then listed 101, 102, 104, 105, 106 and 107 as the open lower-numbered plans ahead of it). **Verified 2026-09-24 from their status lines: `100-SCOPE-RULE-FOLLOW-UPS-PLAN.md`, `101-NON-WEB-STACK-READINESS-PLAN.md` and `102-SPECIFY-IN-PLACE-REVISION-PLAN.md` are DONE (build) and closed, and no root plan file carries the number 103** — so, on the orchestrator's reading, this plan is next in line.
- **Build order:** Phase 1 is independent and may ship alone. Phase 2 → Phase 3 → Phase 4, and **Phase 4 never before Phase 3**; Phase 5 after Phases 2 and 3; Phase 6 after Phase 5; Phase 7 last; Phase 8 user-driven.
- ⚠ **File anchors drift.** `## When resuming work` step 3's re-verification is **the FIRST action of any build session**, not an optional one.

**What this record does NOT close — 2026-09-24.**

- **Nothing is built.** Phases 1–8 have not started. *(True at the close. Added 2026-09-25 at build: Phases 1–6 are now BUILT; Phase 7 is pending and Phase 8 is NOT run.)*
- **No evidence class changed** (**How it closed**).
- **No per-item deliberation happened**, so every counter-argument in this plan is live for re-opening on its own merits.
- **The orchestrator's D3-before-D5 argument is NOT ratified and stays live.** If D3 is ever re-opened onto (d), D5's identity field stops being needed for §3.5–§3.8 and §6.1–§6.4 (D5's 2026-09-24 note), D6 is re-read, and D2's discharge above is re-derived.
- **D2 → (d) and D3 → (a) are the orchestrator's readings of re-opened text under a blanket approval, not maintainer picks.** The maintainer may re-open either.
- **D2(d)'s `install.sh` line was not verified** in the 2026-09-24 re-check; Phase 3 verifies it at build.

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

#### Phase 1 build record — 2026-09-24

*(added 2026-09-25 at build)* **Commit `9981148`, committed on 2026-09-24 — the first commit after the Phase 0 close (`4c61af4`).** ⚠ Build-verified, never consumer-validated; Phase 8 is NOT run.

**What was built:**
- `src/commands/constitute/main.md` — the block is named **"Forcing Functions config block"** at all seven sites. The user-facing echo line now says the block is stored in `.devforge/constitute.json` and is not a numbered section of `constitution.md`.
- `src/CLAUDE.md` — the `#### /devforge:constitute` catalog clause uses the same name.
- Nothing about the forcing-functions mechanism changed.

**Verify, line by line:**
- `grep -rn "Section 3.5" src/` returns nothing.
- The echo line states that the block is a config block and not a numbered `constitution.md` section, and every one of the seven `main.md` sites names it "config block".
- `git diff --stat src/devforge/lib/` is empty for this phase.
- The live-spec tests — **78 passed.**

**Review:** instruction-reviewer — SHIP-READY with one nit: the block name was unified in `src/CLAUDE.md`. Fixed → **SHIP-READY.**

**Suites:** the full `tests/lib` baseline before any build phase, at `4c61af4`: **11818 passed, 16 skipped.** The next full-suite count is in Phase 2's record, on a tree that carries this phase.

### Phase 2 — Rule identity and comparison keying (F4, F9)

**Depends on: D5, then D4.** Not startable while either is open.
**Route: python-engineer → python-reviewer. Every function gets a test written AND run in the same turn. `scripts/constitution-drift-check.sh`'s Check A comment and printed `Fix: re-run …` line ride the same route, and for them the reviewer runs the affected install/update path against a scratch target, never a consumer install.**

- The schema change D5 ratifies, across the surfaces its blast-radius list names: `add-rule`'s CLI surface, `validate`'s Dim 4, `render`, both sides of `_universal.py`, and the tests — **plus D5's pre-change-state obligation**: what the comparator reports on state constituted before the change.
- The comparator keys on whatever D4 ratifies, in `_cmds_quality.py`.
- **The canonical parser's section boundary (F9):** any markdown heading ends a section, and a trailing `---` rule is not body. A parser defect, not a decision — it rides in this phase because it is the comparator's canonical side, and no keying fix can make §3.8 compare equal while its canonical body carries `## 4.`.
- **`scripts/constitution-drift-check.sh`'s Check A comment and printed remediation** — *"Exit 2 == real drift"* and *"Fix: re-run /devforge:constitute to re-synthesize constitution.md + forcing-function config."* (F5). They describe the comparator's semantics, so they change with it and must be true of the built comparator. Shell text, not Python; same route.
- **Not taken (2026-09-24 close) — D5 is ratified (a).** Drafting-time text kept: ⚠ **If D5 is ratified (b) — no identity field — this phase is D4's repair alone** (with F9's boundary and the drift-check text), and its Verify drops every schema bullet. The phase does not silently do (a) anyway.

#### Verify

- **The two sides mean the same thing**, demonstrated by a test that builds a consumer state through the real CLI and asserts the comparator's canonical and consumer key sets are equal for at least one section outside §3.6 and §4.x, and for §3.6 and §4.1 as well.
- **A test asserts §3.8's canonical body contains no line starting `## ` and does not end with `---`** (F9) — `_parse_universal_blocks` run over the live `src/constitution.md`.
- `validate`'s composite on a fully-populated real-producer state is **unchanged** from before this phase, or the change is stated with the number (F7: Dim 4 carries weight 0.20 against a 0.95 gate).
- `render` output on a fully-populated state is byte-identical to before this phase, or every difference is stated — **except the render change D3 ratifies (F10), stated.** Phase 3 owns that change; any part of it D5's schema change forces into this phase is stated here.
- The targeted suite, then the full `tests/lib` suite, is green.
- python-reviewer returns SHIP-READY, or every finding is fixed.

#### Phase 2 build record — 2026-09-25

*(added 2026-09-25 at build)* **Commit `01e3d3a`.** ⚠ Build-verified, never consumer-validated; Phase 8 is NOT run.

**What was built:**
- **F9 — the canonical parser's section boundary.** `_parse_universal_blocks` ends a numbered section at the next heading whose level is equal to or shallower than its own, numbered or not. Headings inside a fenced code block are ignored, and trailing horizontal-rule lines are stripped from the body. Of the parsed canonical bodies, only §3.8's changed. ⚠ **Narrower than this phase's bullet**, which reads *"any markdown heading ends a section"*: a heading deeper than the section's own stays in its body.
- **D5(a) — the identity field is an optional rule field, `name`.** ⚠ **A build choice: `name`, not `label`** — code-example records already carry a field `label` (validated against the `code_label` enum). The field is stored only when given, so existing states, `render` output and `validate` output are byte-identical (verified against HEAD). A duplicate `name` within one section or one pattern bucket is rejected with exit 2 — house precedent: `add-ac`'s duplicate-id rejection.
- **D4(a) — the comparison key.** `tag_or_label` is renamed `name` on both sides, and the comparator keys on it. A consumer rule with no `name` is ignored.
- **D5's pre-change-state obligation — a NEW finding kind, `PRE_IDENTITY`.** ⚠ **An invention beside MISSING and DRIFT, flagged as one.** A state with no named universal rule draws one `PRE_IDENTITY` finding, and the drift check prints one line for it. **Known edge:** a consumer who dropped every universal section draws the same finding.
- **`scripts/constitution-drift-check.sh`** — Check A's comment is corrected, and a `PRE_IDENTITY` line is added. The printed `Fix: re-run …` line is kept: it is true once Phase 3 has landed, because Phase 3 wires `seed-universal` into `/devforge:constitute`.

**Verify, line by line:**
- **Key sets.** `test_name_sets_equal_canonical_for_35_36_41_via_real_cli` builds a consumer state through the real CLI and asserts that the canonical and consumer `name` sets are equal for §3.5 (outside §3.6 and §4.x), §3.6 and §4.1.
- **§3.8's body (F9).** `test_section_38_body_excludes_next_h2_and_trailing_rule` runs the parser over the live `src/constitution.md`.
- **`validate`'s composite** is unchanged from HEAD, and **`render`** output is byte-identical to HEAD — both verified by the reviewer.

**Review:** python-reviewer — SHIP-READY with one MEDIUM and two LOWs. Between them they covered stale test docstrings and a duplicate `name` that silently took the last write, which is now rejected at the producer (above). Fixed → **SHIP-READY**, mutation-checked. The reviewer also verified the `render` and `validate` comparisons against HEAD.

**Suites:** full `tests/lib` — **11835 passed, 16 skipped.**

### Phase 3 — Canonical text delivery, seeding and render (F3, F10, F11)

**Depends on: D2 and D3, and D2 depends on Phase 2's outcome (D5).** Not startable while any is open.
**Route: python-engineer → python-reviewer for the helper work, the `install.sh` line, any `update.sh` line D2(a)'s update path adds, and, under D2(d), the `src/manifest.json` entry — for the shell and manifest lines the reviewer runs the affected install/update path against a scratch target, never a consumer install. instruction-author → instruction-reviewer for doc text only — including, under D2(d), `src/devforge/storage-rules.md`'s class entry, which is markdown.**

- The carrier D2 ratifies.
  - Under (a) — **not taken (2026-09-24 close)**: one added line in `install.sh`'s snapshot block at `:432-434`, copying from `$TEMPLATE_DIR/src/constitution.md` directly (`install.sh:365`'s pattern) and **not** from `$TARGET_DIR` the way the block's existing two lines do. ⚠ **And (a) has no update path** (D2, corrected 2026-09-24): `update.sh` never refreshes `.devforge/template/constitution.md`, so this phase either adds one or states the install-time freeze, per what D2 ratifies.
  - Under (d) — **ratified (2026-09-24 close)**: one `templateOwned.files[]` entry in `src/manifest.json` mapping `src/constitution.md` to a gitignored CODE-class target; whatever line `install.sh`'s own pattern requires (verified at build — not verified in the 2026-09-24 re-check); and the new entry in `src/devforge/storage-rules.md`'s class list.
- The seeding route D3 ratifies. Under (a) — **ratified (2026-09-24 close)**: a new verb that writes all eleven universal sections into `.devforge/constitute.json` from the canonical source, with the helper owning numbers, headings, tags and identities. Under (d) — **not taken (2026-09-24 close)**: `render` emits §3.5–§3.8 and §6.1–§6.4 from the carrier, the state records only their presence, and §4.1–§4.3 stay on `add-pattern-rule`.
- **The render change D3 ratifies (F10)** — this phase owns render's shape, which no phase owned before 2026-09-24. Under D3(a)–(c): a rule renders as a named block — name, prose, nested list and code fence intact — not as a one-line `- [<tag>] <text>` bullet (D3(a) is ratified, so this is the arm that applies). Under D3(d) — **not taken (2026-09-24 close)**: the verbatim emission above.
- The `/devforge:constitute` spec is wired to call it, at a phase that runs before Section 3's and Section 6's echoes.

#### Verify

- A fresh `reset` followed by the seeding route produces a state in which **`_extract_universal_rules_from_state` returns all eleven `_UNIVERSAL_SECTIONS` keys**, each with non-empty rules — under D3(d) (**not taken, 2026-09-24 close**), the consumer side the comparator then reads (the rendered file for §3.5–§3.8 and §6.1–§6.4, the state for §4.1–§4.3) yields all eleven.
- `forge-internal:verify-universal-defaults` against that state and the canonical file **exits 0 with zero findings** — the first time any real-producer state makes that verb exit 0. (A real-producer state was first fed to it on 2026-09-24, in the re-check, and exited 2 with 32 MISSING.)
- **`constitute_helper verify` — the round-trip verb, not only `verify-universal-defaults` — exits 0 on the seeded state** (F9: a state seeded from today's canonical parser fails it with a section-count mismatch).
- **The rendered §3.6 carries every principle name** canonical §3.6 carries — counted live from `src/constitution.md`, each grep-found in the rendered `constitution.md` (F10).
- `validate` on the seeded state reports no unresolved citation that originates in canonical text, or each one is stated with its Dim 2 cost (F11).
- The canonical text reaching the consumer is the shipped template's, not a rendered artifact: the source path is asserted in a test, and `install.sh:364`'s presence guard is untouched (OQ-3) or its change is stated.
- The 27-subcommand count is restated as whatever it now is, **counted live from `add_parser(` call sites, never incremented from memory.**
- Full `tests/lib` suite green; python-reviewer SHIP-READY or every finding fixed.

#### Phase 3 build record — 2026-09-25

*(added 2026-09-25 at build)* **Commit `787cf72`.** ⚠ Build-verified, never consumer-validated; Phase 8 is NOT run.

**What was built:**
- **D3(a) — `seed-universal`**, in `_cmds_seed.py`. It writes all eleven universal sections into `.devforge/constitute.json`, the three `*_universal` pattern buckets included. Its default source is `<devforge-dir>/templates/constitution.md`.
- ⚠ **The orchestrator's reading, recorded — not a maintainer ruling.** `## Tripwires` reads *"No change to §4.1–§4.3's path."* The build reads "path" as their storage path: named `*_universal` buckets, recorded by bucket name and never by a number. That path is unchanged. What moves is the content source, from model memory to the canon — D3(a)'s *"writes all eleven universal sections"* and this phase's Verify (*"all eleven `_UNIVERSAL_SECTIONS` keys"*) both require it. The same reading is recorded, dated, beside the Tripwire's *"They travel `add-pattern-rule`"* and *"never how they are produced"*, and beside `## Non-goals`' *"Changing §4.1–§4.3's production path"*. The project-specific buckets still travel `add-pattern-rule`.
- **D2(d) — the carrier.** `src/manifest.json`'s `templateOwned` maps `src/constitution.md` to `.devforge/templates/constitution.md`. `install.sh` copies it unconditionally from `$TEMPLATE_DIR`, and `update.sh`'s generic `templateOwned` loop refreshes it. Verified on a scratch target: a fresh install, a reinstall over an existing root `constitution.md` — `install.sh`'s presence guard untouched (OQ-3) — and an update. `src/devforge/storage-rules.md` gained the CODE-class file.
- **D2's discharge held** (`**Ordering and conditions**`). `seed-universal` derives every rule identity from the canonical markdown with the parser, so a flat copy sufficed, and D2 is not re-opened.
- **F10 — render.** A named rule renders as a named block, and section arrays render in numeric order. A state holding only unnamed rules renders byte-identical to HEAD.
- **F11 — `validate`'s Dim 2** skips a rule that is both named and tagged universal — a test of shape, not provenance. The reviewer tightened it from "named" alone.
- **`src/commands/constitute/main.md`.** Its Phase 1 runs `seed-universal` after `reset`, and ABORTs on failure. Section 4's universal buckets are seeded, echoed by name, and overridable, with a user-facing drift warning.

**Maintainer decision, 2026-09-25 — asked mid-build through AskUserQuestion: `drop-rule` and `drop-section` (`_cmds_drop.py`).** Seeded content sits in the state before the echo, and no existing verb removed a rule or a section, so ratified D6(a) — overrides stay available against universal sections — was not executable. The maintainer chose to add both verbs. ⚠ They are not in this plan's drafted text.

**A behaviour-preserving restructure**, under `.claude/agents/python-engineer.md`'s file-size rule (over 600 lines without a split is an automatic HIGH). The six forcing-functions subparsers moved into `_forcing_functions/_cli.py`'s `register_subparsers()`. `--help` output for every shared subcommand is byte-identical to HEAD, and `_cli.py` went from 586 to 409 lines.

**Verify, line by line:**
- **All eleven sections.** A fresh `reset` followed by `seed-universal` writes all eleven universal sections, and the comparator (next line) finds none MISSING.
- **The headline.** On that real-producer state, `forge-internal:verify-universal-defaults` **exits 0 with zero findings — the first time a real-producer state has done so** — and `constitute_helper verify` round-trips with exit 0.
- **§3.6 (F10).** The rendered §3.6 carries all nine principle names.
- **F11.** `validate` reports no unresolved citation that originates in canonical text.
- **The source path.** `test_default_canonical_path_is_devforge_dir_templates` asserts `seed-universal`'s default source. `install.sh`'s presence guard is untouched.
- **The subcommand count**, counted live from `add_parser(` call sites: **27 → 30** — 24 in `_cli.py`, 6 in `_forcing_functions/_cli.py`.

**Review:** two loops, each closing SHIP-READY.
- **The markdown — instruction-reviewer:** SHIP-READY with two LOWs. Fixed → **SHIP-READY.**
- **The code — python-reviewer:** SHIP-READY with one MEDIUM and one LOW. Fixed → **SHIP-READY**, mutation-checked.
  - MEDIUM: F11's exemption was keyed on `name` alone. It is tightened to `name` AND a universal tag (above).
  - LOW: seeding replaces a section at a universal number, whatever that section's tag. It is now documented and pinned by `test_seeding_replaces_pre_existing_section_regardless_of_tag`.

**Suites:** full `tests/lib` — **11868 passed, 16 skipped.**

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

#### Phase 4 build record — 2026-09-25

*(added 2026-09-25 at build)* **Commit `c76905d`, after Phase 3's `787cf72` — stated from `git log`, not assumed.** ⚠ Build-verified, never consumer-validated; Phase 8 is NOT run.

**What was built:**
- **D7(a), as the build applied it.** Section numbers are fixed. The four universal sub-sections, 3.5–3.8, are always present: seeded, and removed only by a user override that maps to `drop-section`. Project-specific sub-sections number consecutively from 3.1, zero to four of them, never past 3.4. Section 6 composes zero to two, at 6.5 then 6.6.
- **A correction from review.** The headings of the project-specific slots are the project's own dimensions; the canonical ones are typical, not mandated (D7: *"3.1–3.4 are examples, not a mandate"*).
- *"4-7"* is gone. Every universal number in `constitute/main.md` and `references/section-shapes.md` was checked pairwise against the canon.
- **The CBM-first rule's home** is Section 6's project workflow sub-section — typically *"Project-Specific Workflow"*, at 6.6, or at 6.5 when it is the only composed one. **Why:**
  - it applies only when the CBM hooks are present, so it is project-conditional, not universal;
  - it is a working-process rule;
  - canonical 6.4 Documentation is seeded, so nothing is composed into it.

  Its companion rule is re-tagged `project-specific`.
- **D6(a) for Sections 2, 3, 5 and 6.** An override maps to `drop-rule`, `add-rule` or `drop-section` against the seeded state. An override naming a number the echo did not show is re-prompted.
- **D5's user-facing half — a verified no-op.** The `[<tag>]` override grammar is unchanged: a user-added rule carries a tag and no name.

**Verify, line by line:**
- Both greps this Verify names — the old sub-section names, and `4-7` — return nothing.
- Every universal number named in both files matches a heading in `src/constitution.md` at that number, checked pairwise.
- The CBM-first rule names a sub-section that exists in the canon; which one and why are recorded above.
- `git log` shows `787cf72` before `c76905d`.
- The live-spec tests — **78 passed.**

**Review:** instruction-reviewer — **NEEDS-FIX** at first, with three findings:
- MEDIUM: project-specific headings were over-pinned. This is the correction above.
- LOW: adding a rule to a number the echo did not show.
- LOW, **deferred to Phase 7**: the example in `src/agents-AUTHORING.md`.

The first two were fixed → **SHIP-READY.**

### Phase 5 — The tests onto the real-producer principle (OQ-1)

**Depends on: OQ-1, and on Phases 2 and 3 having landed** (a real-producer in-sync fixture is unbuildable before them).
**Route: python-engineer → python-reviewer.**

- The `TestForgeInternalVerifyUniversalDefaults` fixtures, per OQ-1.
- `test_verify_universal_defaults_passes_with_38_in_sync` and `test_verify_universal_defaults_detects_missing_38`, which share the same hand-authored builder or a bare `default_state()` (F5).
- `_build_in_sync_constitute_json`'s docstring, whose *"Fixture strategy"* paragraph explains a constraint this plan removes.
- `test_render_from_seeded_state_includes_design_fidelity` in `TestDesignFidelityUniversalSection` *(added 2026-09-24)* — a sixth hand-authored fixture that writes the canonical label into `tag` (it builds `{"tag": r["tag_or_label"], "text": r["body"]}` rows). On 2026-09-24 `grep -n '"tag": r\["tag_or_label"\]' tests/lib/test_constitute_helper.py` returns 5 hits: 3 in `_build_in_sync_constitute_json`, 1 in the drift test, 1 in this render test.
- Every rewritten fixture that takes canonical text from `_parse_universal_blocks` takes it after Phase 2's boundary fix (F9) — before it, §3.8's canonical body carries `## 4.`.

#### Verify

- **At least one test feeds a state built through the real CLI to `verify-universal-defaults` and asserts exit 0.** That test is named in this phase's record as the one that would have caught F4.
- The MISSING and DRIFT tests still fail-when-they-should: one asserts MISSING on a genuinely absent section, one asserts DRIFT on a genuinely altered body, **both on real-producer states**.
- No surviving fixture writes a value into `tag` that `add-rule` would reject. `grep -n '"tag": r\["tag_or_label"\]' tests/lib/test_constitute_helper.py` returns nothing, or every survivor is stated with its reason.
- Full `tests/lib` suite green; python-reviewer SHIP-READY or every finding fixed.

#### Phase 5 build record — 2026-09-25

*(added 2026-09-25 at build)* **Commit `760b8b7`.** ⚠ Build-verified, never consumer-validated; Phase 8 is NOT run.

**What was built:**
- `_build_in_sync_constitute_json`, the hand-authored builder, is deleted, together with its *"Fixture strategy"* docstring. The in-sync baseline is now built through the real CLI: `reset`, then `seed-universal`.
- The MISSING and DRIFT tests run on real-producer states. MISSING comes from a `drop-section`. DRIFT comes from a `drop-rule` followed by an `add-rule --name` with an altered body.

**Verify, line by line:**
- **`test_verify_universal_defaults_in_sync` is the test that would have caught F4.** It feeds a state built through the real CLI to `verify-universal-defaults` and asserts exit 0.
- **The MISSING and DRIFT tests fail when they should, and both are mutation-checked.** Disabling either comparator branch fails its test. The source was restored byte-identical afterwards.
- `grep -n '"tag": r\["tag_or_label"\]' tests/lib/test_constitute_helper.py` returns nothing. **One hand-authored fixture is left, and stated: `_fully_populated_state()`.** It predates plan 104, it is never fed to the universal comparator, and it writes only valid enum tags.

**Review:** python-reviewer — SHIP-READY with two LOWs: unchecked setup calls, and missing see-also cross-references. Fixed → **SHIP-READY.**

**Suites:** the constitute tests — **496 passed, 2 skipped**; full `tests/lib` — **11868 passed, 16 skipped.**

### Phase 6 — The drift-claim question (OQ-2)

**Depends on: OQ-2, and on Phase 5** (the after half needs the real-producer fixture; the before half is runnable today and was baselined on 2026-09-24).
**Route: instruction-author → instruction-reviewer for the amendments; the run itself is an observation recorded in this plan.**

- Run the before/after OQ-2 names and **record the result as a fact with its numbers**, in this plan's build record. The before half re-runs at build time against the canon then current; the 2026-09-24 baseline (32 MISSING / 0 DRIFT / exit 2, canon at `6a786b3`) is a comparison point, not a substitute.
- If established: dated amendments — never rewrites — at the **plan-file** claim sites only: `89-TEST-FOUNDATION-HARDENING-PLAN.md`, `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md`, and `44-CONSTITUTION-DRIFT-WIRING-PLAN.md`'s *"~30 MISSING"* / *"29 MISSING findings"* records (F5). **Released `CHANGELOG.md` sections are never edited** — the correction for `## [2.0.10]` (the `86-FOWLER-REFACTORING-GAPS-PLAN.md` and `89-…` claims) and `## [2.0.12]` (the `99-…` claim) rides in Phase 7's `## [Unreleased]` entry. `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`'s D7 is recorded in this plan as whether its cost premise held — never amended.
- If not established, or indistinguishable: record that, and amend nothing.

#### Verify

- The run's result is recorded as a NUMBER on both sides (findings before, findings after), not as a characterization.
- Every amendment is **dated and additive**; no ratified sentence in plans 44, 86, 89 or 99, or in `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`, is rewritten or deleted.
- **No released `CHANGELOG.md` section is edited** — this phase's diff does not touch `CHANGELOG.md` at all.
- ⚠ The amendments say what was established and what was not. **"Indistinguishable" is a legitimate result and is recorded as one**, not smoothed into either conclusion.
- `grep -rniE "designed consumer drift|consumer-install drift|verify-universal-defaults" --include=*.md .` is classified in full: each hit is an amended site, a released `CHANGELOG.md` section left as released, history, or this plan's own quote of one.

#### Phase 6 build record — 2026-09-25

*(added 2026-09-25 at build)* **The Phase 6 commit — the one that carries this record and the Status line.** The run is an observation, recorded here. ⚠ Build-verified, never consumer-validated; Phase 8 is NOT run.

**The OQ-2 run** was reproduced twice, the second time at `760b8b7`. One state was built through the real CLI to match the canon exactly: `reset`, then `seed-universal --canonical-path src/constitution.md`, with the canon at `6a786b3`.
- **Before the fix** (the comparator with lib at `9981148`): **exit 2, 32 findings, all MISSING, across all eleven universal sections.** This matches the 2026-09-24 baseline (32 MISSING / 0 DRIFT / exit 2).
- **After the fix** (lib at `760b8b7`): **exit 0, 0 findings.**

**Established:** the drift findings plans 86, 89 and 99 predicted, and plan 44's *"~30 MISSING"* / *"29 MISSING findings"*, were indistinguishable from a comparator artifact — the comparator before the fix reports a count of that size for a state in sync with the canon. **Not established:** whether any particular install also had real drift.

⚠ **The build took the *"If established"* branch, and amended.** What the run established concerns the counts — in plan 44's amendment, *"A count of that size therefore cannot show drift."* Whether any install also drifted stays recorded as not established; it is not smoothed into either conclusion.

**Amendments — each dated and additive:**
- **Seven OQ-2 amendments:**
  - `89-TEST-FOUNDATION-HARDENING-PLAN.md` — four, including its status header and anchor 3. The amendment restates anchor 3's expected result as one `PRE_IDENTITY` finding for an install constituted before plan 104.
  - `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md` — two.
  - `44-CONSTITUTION-DRIFT-WIRING-PLAN.md` — one, plus two pointer lines to it.
- **One D3(a) note in `89-TEST-FOUNDATION-HARDENING-PLAN.md`.** It records that plan 104 took that plan's *"universal sections seeded mechanically"* subject.
- **Two drift-claim sites the Verify grep below does not reach, classified HISTORY and not amended.** Both are deliberation or dependency notes whose claims are corrected at the amended implementation sites:
  - `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md` — D2's *"Counter-argument to (a)"* (grep `third universal-defaults drift finding`);
  - `89-TEST-FOUNDATION-HARDENING-PLAN.md` — a bullet under `## Dependencies + related` (grep `drift-on-old-installs recorded as designed`, and `consumers see two drift findings` two lines below it).
- **No released `CHANGELOG.md` section is edited.** The correction rides in Phase 7's `## [Unreleased]` entry.

**`108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`'s D7 — recorded, never amended.** Its premise was that a §6.1 edit costs *"a fourth drift finding for installs constituted earlier"*. Before plan 104 that cost was zero, because every constituted install already saw every universal rule reported MISSING. After plan 104 the cost is real for installs constituted after it — a genuine per-rule finding — and an install constituted before it sees a single `PRE_IDENTITY` line. **So the premise did not hold at the time; it holds from here on.**

**Verify, line by line:**
- The result is a number on both sides: **32 findings before, 0 after.**
- Every amendment is dated and additive (the list above).
- No released `CHANGELOG.md` section is edited.
- What was established and what was not are stated above, and "indistinguishable" is recorded as the result.
- **`grep -rniE "designed consumer drift|consumer-install drift|verify-universal-defaults" --include=*.md .`, classified in full** — on 2026-09-25, by the orchestrator, over the full-repo run (22 files). **This Verify line reads met.**
  - **Plans 89, 99 and 44** — amended sites and history, as recorded above.
  - **This plan's own text.**
  - **`108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`** — D7, recorded here and never amended.
  - **`CHANGELOG.md`** — released sections left as released, plus the new `## [Unreleased]` entry.
  - **The repo `CLAUDE.md`'s router row and `DEVELOPMENT-STATUS.md`** — Phase 7's new text.
  - **`PLAN-STATUS-ARCHIVE.md`** — the designed-drift lines in the plan 86, 89 and 99 ledger entries, at about lines 77, 90, 235, 241 and 258 on 2026-09-25. They are classified HISTORY: finished-plan ledger records. This plan's archive entry states the OQ-2 finding.
  - **Plans 41, 57 and 60** — they name the verb as a mechanism, so they are unrelated to the drift claims.
  - **Plans 66, 90 and 97, and `done-plans/*`** — finished-plan history.
  - **`src/commands/specify/main.md`** (grep `verify-universal-defaults`; line 786 on 2026-09-25) — a live spec line telling maintainers to run the verb. It is still true, and the verb can now return green.

**Review:** instruction-reviewer — SHIP-READY with one MEDIUM and two LOWs. Fixed → **SHIP-READY.**
- MEDIUM: plan 89's seeding note cited OQ-2. It now cites D3(a).
- LOW: plan 44 gained its local pointers.
- LOW: the grep's reach gap. It is recorded here — the two HISTORY sites above.

**Open after the Phase 1–6 build — 2026-09-25:**
- **Phase 7, the docs sweep, is pending. Phase 8 is NOT run**, so "built and reviewed" is the ceiling of every claim in this plan.
- **One review finding is deferred to Phase 7:** Phase 4's LOW on the example in `src/agents-AUTHORING.md`.
- **Side findings, NOT fixed — outside this plan's scope:**
  - `install.sh` never ships `src/devforge/storage-rules.md`; only `update.sh` does.
  - `_configure/_lint_ignore.py` emits a `SyntaxWarning` (invalid escape sequence) on import. The stub `121-HELPER-SYNTAX-WARNINGS-PLAN.md` names it.
  - `src/devforge/lib/.pytest_cache/` exists on disk in this checkout, under the `templateOwned` lib glob.
- ⚠ **The evidence class is unchanged:** F1 observed once; F4, F9, F10 and F11 reproduced on 2026-09-24 on a scratch state built through the real CLI (reproductions, not consumer incidents); F2 and F3 found by reading; nothing measured on any consumer.

### Phase 7 — Docs sweep

**Route: instruction-author → instruction-reviewer. Docs only, plus one `update.sh` comment (a comment, no executable line).** Apply F8 before touching any ledger.

- `CHANGELOG.md` — a new entry under `## [Unreleased]`, **evidence class first and honest bounds last**. If Phase 6 established the artifact finding, this entry also carries the correction for the released `## [2.0.10]` and `## [2.0.12]` drift claims — **those released sections are never edited.**
- `DEVELOPMENT-STATUS.md` — an edit or a recorded verified no-op.
- Repo `CLAUDE.md` — **the "Where to find what" router's constitute / forcing-functions rows ONLY**: an edit or a recorded verified no-op. ⚠ **No index line goes here, and no pointer to the archive either** — that file carries no plan status at all.
- `PLAN-STATUS-ARCHIVE.md` — **two sites in one file**: this plan's one-line entry in `## Index`, in the house shape its neighbours there use, and a new full entry in `## Entries` in the archive's house shape. `## Entries` is the authority; the `## Index` line summarizes it and never competes with it.
- `README.md` — **an EDIT, not a verified no-op** (corrected 2026-09-24). Its sentence *"When a release changes a universal constitution section, the update prints a WARN-only drift notice naming the drifted sections and exits normally; re-run `/devforge:constitute` to adopt the new wording."* (grep `WARN-only drift notice`) must be true of the built state. ⚠ **It is false TODAY (F5), so it may be corrected ahead of the build**, in the same "may ship alone" spirit as Phase 1 — **the maintainer's call, not decided here.**
- `update.sh` — the neighbouring false comment F5 records, *"Project customizations live in CLAUDE.md / constitution.md / agents — those still three-way merge upstream."* (grep `Project customizations live in`): it stops naming `constitution.md` as three-way merged. One comment, no executable change.
- `src/agents-AUTHORING.md` — the example deferred from Phase 4's review (LOW): an edit or a recorded verified no-op. *(added 2026-09-25 at build)*

#### Verify

- Every site is recorded as an **edit or an explicit verified no-op, with the grep that shows it.**
- `README.md`'s drift sentence (grep `WARN-only drift notice`) is true of the built state, and the `update.sh` comment (grep `Project customizations live in`) no longer names `constitution.md`.
- `src/agents-AUTHORING.md`'s example — the one deferred from Phase 4's review — is live and consistent with `src/commands/constitute/references/section-shapes.md`. *(added 2026-09-25 at build)*
- `grep -rn "104-UNIVERSAL" --include=*.md .` returns `PLAN-STATUS-ARCHIVE.md` **twice — once under `## Index`, once under `## Entries`** — plus this file, at minimum. ⚠ It returns **no** repo `CLAUDE.md` hit; one there is a line this phase must not have written.
- No summary anywhere claims consumer validation. **"Built and reviewed" is the ceiling** until Phase 8 runs.
- The evidence class is attached at every site: F1 observed once; F4, F9, F10 and F11 reproduced on 2026-09-24 on a scratch state built through the real CLI (reproductions, not consumer incidents); F2 and F3 found by reading; nothing measured on any consumer.
- No tracked file names a client, a client component, a client ticket or a benchmark path.

### Phase 8 — Consumer e2e — user-driven HARD GATE, NOT run

**Everything above is build-verified at best, never consumer-validated, until this phase runs.**

- **Fixture:** a testForge20 install. **The frozen benchmark install is never touched.**
- The anchors are known-answer cases, **scored in PAIRS**:

1. **A fresh `/devforge:constitute` run on a constituted-from-scratch fixture** → the rendered `constitution.md` carries §3.5, §3.6, §3.7, §3.8, §6.1, §6.2, §6.3 and §6.4 **at those numbers with those headings** (number and title; Section 6's render omits the `[universal]` suffix today — `include_tag_suffix=False`), and the bodies meet the check D3's outcome sets (F10): **under D3(d)** — **not taken (2026-09-24 close)** — each rendered universal sub-section's body equals the canonical body byte-for-byte after whitespace normalization; **under D3(a)–(c)**, each equals the canonical body after the render change D3 ratifies, with §3.6's principle names present. Phase 0 ratified D3(a) (2026-09-24 close), so **the D3(a)–(c) statement is the one scored.** **PAIRED WITH 2.**
2. **`forge-internal:verify-universal-defaults` against that same install** → **exit 0, zero findings.**
3. **The same install with one universal rule deliberately altered** → exit 2 with **exactly that section** in the findings, and no other.
4. **A `/devforge:constitute` run read by a human at the forcing-functions echo** → the user-facing line does not name the block by a `3.x` number, and nothing in the transcript invites a reader to confuse it with §3.5. (Phase 1's anchor; it stands alone if Phase 1 ships alone.)
5. **An `update.sh` run against an install constituted AFTER the fix, with nothing drifted** → **no constitution-drift warning at all.** ⚠ This is the anchor that tests F5's user-visible consequence, and it is the only one that would show the warning noise gone. **PAIRED WITH 5b.**
   - **5b — an `update.sh` run against an install constituted BEFORE the fix** → exactly the output D5 ratifies for pre-change state (D5's blast radius: the drift check always pairs the new helper with old state) — e.g. one line naming re-constitution, never one MISSING per rule. **PAIRED WITH 5.**

#### Verify

- Every anchor is scored **explicitly** — stated, not summarized — with the pair scored together.
- **If an anchor fails,** record the negative with the artifacts and name the mechanism before proposing any fix: a wrong number or heading is D7 / Phase 4; an invented body is D2 / D3 / Phase 3; a false MISSING is D4 / D5 / Phase 2; a duplicated `## 4.` heading or a round-trip `verify` failure is F9 / Phase 2; a missing §3.6 principle name or a universal body collapsed into one bullet is F10 / D3 / Phase 3; a per-rule MISSING flood on anchor 5b is D5's pre-change-state answer / Phase 2; a false green on anchor 3 is a comparator that stopped comparing; a surviving label collision is Phase 1. **They have different fixes.**
- **A clean run shows the chain behaves on planted fixtures, never that any of these gaps cost anything** — F1 is the only observed item, and it is a label, not a mechanism.

---

## Honest bounds

- **No consumer incident for F2, F3, F4, F9, F10 or F11.** The only observed thing is F1's label confusion in a real run. F2 and F3 were found by reading; F4, F9, F10 and F11 were reproduced on 2026-09-24 on a scratch state built through the real CLI — reproductions, not consumer incidents. **Nothing was measured on any consumer** — not how many consumers have a wrong-numbered §3.5, not how much universal text is missing from any install, not how often the drift warning fires, not what F11's citation costs a real consumer's `validate` composite.
- **The framework currently has no production installs, only test ones** (maintainer, 2026-09-20). **So there is no backward compatibility to preserve and no data migration owed** — which is the reason the more invasive options (D4(a), D5(a)) stay on the table rather than losing to the cheapest compatible repair. ⚠ If that stops being true before this plan ships, D4 and D5 must be re-argued, not inherited. ⚠ **Refined 2026-09-24: the comparator's behaviour on pre-change state IS owed**, whatever the install count — the drift check always runs the NEW helper against OLD state (D5's blast radius). The frozen benchmark install, a consumer install on an older version, meets that behaviour on whatever update it next receives, if it holds a `.devforge/constitute.json` (the drift check is silent without one).
- **A green `verify-universal-defaults` test run is not evidence the detector works.** Today five such tests pass against a comparator that cannot return green on a real install (F4, F5). Only a real-producer in-sync fixture asserting exit 0 is evidence, and it does not exist yet. *(Added 2026-09-25 at build: it exists now — `test_verify_universal_defaults_in_sync`, `#### Phase 5 build record — 2026-09-25`.)*
- **F5's artifact question is not settled by this plan's reading.** F4 says the comparator cannot return green; it does not say the specific installs plans 44, 86, 89 and 99 describe had no real drift. They may have had both. Nor does it say `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`'s D7 cost premise was wrong — it makes that premise a candidate too. OQ-2 establishes it by a run or records that it could not.
- **Nothing mechanical checks that the model composed the canonical text.** After every phase here, `validate`'s dimensions and `verify-universal-defaults` are the only nets, the second is advisory and WARN-only at install/update time, and neither runs inside a `/devforge:constitute` session at the moment a sub-section is composed. *(Added 2026-09-25 at build: since Phase 3 the model composes no canonical text — `seed-universal` writes it — and `verify-universal-defaults` can now return green. It stays advisory and WARN-only at install/update time, and it still does not run inside a `/devforge:constitute` session.)*
- **D6(a) knowingly ships an unsilenceable warning** for a user who deliberately overrides a universal rule, and a warning that is learned-past trains a user past the real ones too. Accepted, with (c) recorded as the named strengthening arm and its trigger stated.
- **Phase 4 without Phase 3 is worse than today.** Correct numbers with no text source replaces a loud absence with a quiet invention. This is an argument from reasoning, not from an observed run.

---

## Tripwires

- **Plan 75's tripwire, both halves: zero new `verify-*` gates, zero new check numbers, zero new hard-fail validators.** This plan repairs an existing advisory detector and adds no gate. `verify-universal-defaults` stays WARN-only and fail-soft at `install.sh` / `update.sh`; nothing here makes it block.
- **No edit to `src/constitution.md`.** The canonical file is the thing everything else is measured against; editing it inside this plan would move the target mid-repair. Any constitution amendment is a separate plan with its own designed-drift note.
- **No back-porting into shipped installs.** They arrive via `install.sh` / `update.sh`. The frozen benchmark install is never touched.
- **Code is confined to Phases 2, 3 and 5** (delivery, keying, tests). The code in them: Python helpers and tests (Phases 2, 3 and 5); `scripts/constitution-drift-check.sh`'s Check A comment and its printed `Fix: re-run …` line (Phase 2); the `install.sh` line D2(a) or D2(d) requires, any `update.sh` line D2(a)'s update path adds, and, under D2(d), the `src/manifest.json` `templateOwned` entry (Phase 3). Phases 1, 4, 6 and 7 are instruction and docs only — Phase 7's one `update.sh` comment included, as a comment with no executable change.
  - Every code edit named above — Python, shell, manifest — goes python-engineer → python-reviewer, with a test for every Python function, run in the same turn. For the shell and manifest lines the reviewer runs the affected install/update path against a scratch target, never a consumer install.
  - Every markdown edit, and Phase 7's single `update.sh` comment (no executable line), goes instruction-author → instruction-reviewer.
  - Every new Claude Code fact is checked through `claude-code-guide`.
- **No change to §4.1–§4.3's path.** They travel `add-pattern-rule`, which appends to a named `patterns_and_antipatterns` bucket and records that bucket name, never a number; their numbers are fixed in `src/constitution.md`'s own `### 4.1`, `### 4.2` and `### 4.3` headings, and no number here is ever composed by the model. D4 and D5 touch how their rules are **compared** — the side `_PATTERNS_BUCKET_TO_SECTION` serves — never how they are produced. D3(d) is drafted for §3.5–§3.8 and §6.1–§6.4 only for this reason. *(Added 2026-09-25 at build — ⚠ **the orchestrator's reading, not a maintainer ruling**; `#### Phase 3 build record — 2026-09-25`. Under ratified D3(a), `seed-universal` writes the three universal buckets, using the same bucket names and the same rule shape `add-pattern-rule` writes. The storage path is unchanged; the content source moved from model memory to the canon. So *"They travel `add-pattern-rule`"* now holds for the project-specific buckets only, and *"never how they are produced"* holds for D4 and D5 — the change to how they are produced is D3(a)'s.)*
- **Counts are counted live, never incremented from memory.** The 27 subcommands, the eleven `_UNIVERSAL_SECTIONS` entries, the eight Section 3 sub-sections, the five `verify-universal-defaults` tests, the 32 canonical rules the comparator splits today — re-derive each one at build time and state the number you counted.
- **No `disable-model-invocation` change.** `/devforge:constitute` stays human-typed-only; this plan moves no flag and contributes no count delta.

---

## Non-goals

- **A new `verify-*` gate or a new check number.** Plan 75's tripwire, both halves.
- **Editing `src/constitution.md`.**
- **Back-porting into shipped installs**, and anything specific to the frozen benchmark install.
- **Changing §4.1–§4.3's production path** (`add-pattern-rule` appending to the `patterns_and_antipatterns` bucket). *(Added 2026-09-25 at build — ⚠ **the orchestrator's reading, not a maintainer ruling**; `#### Phase 3 build record — 2026-09-25`. Under ratified D3(a), `seed-universal` writes the three universal buckets, using the same bucket names and the same rule shape `add-pattern-rule` writes. The storage path is unchanged; the content source moved from model memory to the canon. The project-specific buckets still travel `add-pattern-rule`.)*
- **Making `verify-universal-defaults` blocking.** It is advisory at `install.sh` / `update.sh` and stays advisory.
- **Removing the root `constitution.md` copy** (OQ-3's alternative) — a separate decision with its own blast radius.
- **Rewriting any ratified sentence in plans 44, 86, 89 or 99, or in `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`, and editing any released `CHANGELOG.md` section.** OQ-2's remedy is dated additive amendments to plan files, plus a correction in a new `## [Unreleased]` entry.
- **Reopening `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`'s ratified D7.** OQ-2 records whether its cost premise held; the decision stays that plan's.
- **Deciding whether prior drift findings were artifacts, from reading.** OQ-2 establishes it by a run or records that it could not.
- **Touching a plan file this session did not create.** Ownership is established from `git status` and from which sessions are active in this checkout, never from a plan's number (F8).

---

## Context for next session

⚠ **Evidence class, repeated: F1 was observed ONCE, in a real run, as a label confusion. F4, F9, F10 and F11 were REPRODUCED on 2026-09-24 on a scratch state built through the real CLI — reproductions, not consumer incidents. F2 and F3 were found by READING. Nothing was measured on any consumer, and no consumer incident stands behind the mechanism half of this plan.** ⚠ All line digits drift — grep the quoted text. The 2026-09-24 re-check (`### Re-check (2026-09-24)`) added F9–F11 and lists every sentence it corrected in place.

**The one sentence that governs everything here:** the chain that puts universal sub-sections into a consumer's `constitution.md` is unclosed at every link — wrong numbers, no text source, a render that cannot carry the text, a detector that cannot return green, and tests that hide it.

### The 2026-09-20 reverted session — what happened and what carries forward

On 2026-09-20 a session fixed F1 and F2 directly in the tree: the user-facing echo line, all seven label sites, the canonical numbers in both commands and the reference file, plus two consequential doc fixes. **Every one of those edits was then reverted**, when the maintainer observed the work should have been a plan rather than a series of audit fixes. **Nothing from that session survives in the tree**, and this plan assumes none of it — the facts above were re-checked against the live tree after the revert.

Two things from it carry forward, and both are load-bearing:

1. **F4 was discovered during that session** and is recorded in this project's memory as `verify-universal-defaults-broken`. That memory note and this plan are the only places it exists. *(True when written. Added 2026-09-25 at build: the fix is in the tree — Phases 2 and 5 — and Phase 6's amendments in plans 44, 89 and 99 record the pre-fix comparator's output.)*
2. **An attempted fix of F2 alone would have changed the failure mode rather than removing it.** With correct numbers and no body-text source, the model produces the canonical heading at the canonical number and **invents** the body — which is **quieter than the current absence, not louder**, and, once the comparator's keying (F4) is repaired, downgrades the detector's signal from MISSING to DRIFT. **That is the argument for treating delivery (F3) as inseparable from numbering (F2)**, and it is why Phase 4 carries a hard ordering rule rather than a preference.

### Traps

*(added 2026-09-25 at build)* ⚠ **These traps describe the tree before Phases 1–6.** Traps 1, 3, 7, 8 and 11 name defects that Phases 1, 5, 5, 2 and 2 removed, in that order — read each one against that phase's build record.

**Trap 1 — reading "Section 3.5" as the constitution's §3.5.** In `constitute/main.md` and `src/CLAUDE.md` it names the **forcing-functions config block**, which targets a top-level `.devforge/constitute.json` key and can never render as a numbered sub-section. The constitution's §3.5 is *Universal Code Quality*. This collision is F1 and it is the whole of Phase 1.

**Trap 2 — fixing the numbers first.** See above. Phase 4 must not ship before Phase 3.

**Trap 3 — trusting a green `verify-universal-defaults` suite.** Five tests pass today against a comparator that cannot return green on a real install. Until a real-producer in-sync fixture asserts exit 0, a green suite is evidence of nothing here.

**Trap 4 — assuming `verify-universal-defaults` is maintainer-only.** `scripts/constitution-drift-check.sh` calls it from `install.sh` and `update.sh`. Under F4 every constituted consumer sees its warning on every update. It is WARN-only and fail-soft — it never blocks — but it is user-visible.

**Trap 5 — concluding that plans 86 / 89 / 99's designed drift was an artifact.** F4 makes it a candidate, not a finding. OQ-2 settles it with a before/after run or records that it could not. `44-CONSTITUTION-DRIFT-WIRING-PLAN.md`'s *"~30 MISSING"* is a fourth candidate on the same footing — **a count F4 predicts for an in-sync install as readily as for a drifted one.** `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md`'s D7 cost premise is a fifth — recorded, never reopened here. And never "correct" a claim inside a released `CHANGELOG.md` section: the `86-FOWLER-REFACTORING-GAPS-PLAN.md` claim lives only there, so its correction can only be a new entry.

**Trap 6 — deciding D2 before D5.** D5 decides whether a rule has an identity separate from its tag; that changes what the canonical-text carrier must carry. A carrier chosen first is a carrier chosen blind.

**Trap 7 — smuggling a name into `tag`.** It is exactly what the hand-authored fixtures do, and it is what the real CLI rejects. `validate`'s Dim 4 is mechanical at threshold 1.0 with weight 0.20 against a 0.95 human gate — a smuggled label costs the composite and a non-enum value fails outright.

**Trap 8 — treating §4.1–§4.3 as part of the numbering problem.** Their numbers are fixed in `src/constitution.md`'s own `### 4.1`, `### 4.2` and `### 4.3` headings, and `add-pattern-rule` records a bucket name rather than a number — no number here is composed by the model. `_PATTERNS_BUCKET_TO_SECTION` (`_schema.py`) is on neither the setter path nor the render path; its one use site is the consumer-side extractor in `_universal.py`. So they share the **comparison** defect (their consumer-side key is `rule.tag` too) and none of the composition defect.

**Trap 9 — reading `install.sh`'s root `constitution.md` copy as a text source.** It is presence-guarded, uninstructed, and on any re-run holds the previously rendered artifact. F3.

**Trap 10 — a clobbered ledger edit.** Other sessions build in this checkout, and their plan files appear, move and get renumbered without warning (F8). Re-read `git status`, read each ledger live, commit by explicit path, and **never touch a plan file this session did not create** — ownership is established from `git status` and from which sessions are active, never from a plan's number.

**Trap 11 — trusting the canonical parser's §3.8 body.** `_parse_universal_blocks` treats only `N.N` headings as boundaries, so §3.8's body runs through the `---` rule and swallows `## 4. Patterns & Anti-Patterns` (F9). Seed from it and `constitute_helper verify` fails the round-trip; compare against it and a correctly composed §3.8 reports DRIFT forever. Every current fixture that seeds §3.8 takes it from this parser, so those tests carry the same swallowed text on both sides and agree.

### File anchors

- `src/commands/constitute/main.md` — the four input captures; the Section 3 and Section 6 compose paragraphs; the per-section echo template and its override footer; the Section 3.5 echo template and its setter block; the render contract paragraphs.
- `src/commands/constitute/references/section-shapes.md` — the Section 3 and Section 6 blocks; the universal-dimension example; the CBM-first protocol rule.
- `src/constitution.md` — **read-only here.** §3.1–§3.8, §6.1–§6.6, and the `## Rule Tags` section; the `---` and `## 4. Patterns & Anti-Patterns` after §3.8 (F9); §6.1's `plan.md` token (F11).
- `src/devforge/lib/_constitute/` — `_universal.py` (both comparison sides; `_parse_universal_blocks`'s heading regex, F9), `_cmds_quality.py` (the comparator), `_schema.py` (`_UNIVERSAL_SECTIONS`, `_PATTERNS_BUCKET_TO_SECTION`, the `rule_tag` enum), `_validate_metrics.py` (Dim 2, F11; Dim 4), `_cmds_set.py` (`cmd_add_rule`, `cmd_add_pattern_rule` — Phase 2), `_cmds_render.py` (`cmd_verify`'s section walk under *"Check 2: Section arrays"*, its rule-tag check against `ENUM_FIELDS["rule_tag"]` — Phase 2, and the round-trip identity check F9 trips), `_render.py` (`_render_section_body`, `_render_pattern_bucket`, `_render_constitution` — the render walk; F10), `_cli.py` (the 27 subparsers — *30 on 2026-09-25, across `_cli.py` and `_forcing_functions/_cli.py`; `#### Phase 3 build record — 2026-09-25`*).
- `tests/lib/test_constitute_helper.py` — `TestParseUniversalBlocks`, `TestExtractUniversalRulesFromState`, `TestForgeInternalVerifyUniversalDefaults`, `_build_real_constitute_state`, `_build_in_sync_constitute_json`, the two §3.8 verify tests, and `TestDesignFidelityUniversalSection`'s `test_render_from_seeded_state_includes_design_fidelity`.
- `install.sh` — the constitution presence guard and drift-check call; the `.devforge/template/` snapshot block.
- `update.sh` and `scripts/constitution-drift-check.sh` — the drift-check wiring; the drift check's header comment (new helper, old state — D5); Check A's comment and printed remediation (Phase 2); `update.sh`'s `Project customizations live in` comment (Phase 7).
- `src/manifest.json` — `templateOwned`, `templateDerived`, `projectOwned` (D2). `src/devforge/storage-rules.md` and `src/files/devforge.gitignore` — the CODE class and the tracked `.devforge/template/` (D2).
- `README.md` — the drift sentence (grep `WARN-only drift notice`; F5, Phase 7).
- `CHANGELOG.md` — the released `## [2.0.10]` and `## [2.0.12]` drift claims, **read-only** (OQ-2); `## [Unreleased]` (Phase 7).
- Other plans, **cited and never edited except as OQ-2 / Phase 6 allow**: `44-CONSTITUTION-DRIFT-WIRING-PLAN.md`, `86-FOWLER-REFACTORING-GAPS-PLAN.md`, `89-TEST-FOUNDATION-HARDENING-PLAN.md`, `99-SCOPE-FOLLOWS-USER-VISIBLE-BEHAVIOR-PLAN.md`, `108-SCOPE-RULE-DOWNSTREAM-REGIME-PLAN.md` (never amended), `80-CONSTITUTE-CITATION-FALSE-POSITIVE-PLAN.md` (another session's file; never touched).
- `src/CLAUDE.md` — **read-only except Phase 1's one clause** in the `#### /devforge:constitute` entry.

---

## When resuming work

1. **Read this plan in full** before touching anything — it encodes context that is not in the conversation, including a reverted session whose edits are not in the tree.
2. **Read `## Phase 0 close record` first** — it **reads CLOSED 2026-09-24**: D1–D7 and OQ-1–OQ-3 ratified as recommended, D2 → (d) and D3 → (a) by the orchestrator's reading of their re-opened standing text. Build phases may start, and **the record — not the decisions above it — is what says what each phase must do.** ⚠ **The close was a single blanket directive with no per-item deliberation, so every counter-argument in this plan is still live on its own merits**, and the orchestrator's D3-before-D5 argument is recorded there, unratified. *(Added 2026-09-25 at build: first read the Status line, then the close record, then each phase's build record. **Phases 1–6 are BUILT** — Phase 1 on 2026-09-24, Phases 2–6 on 2026-09-25 — and each carries a `#### Phase N build record` directly after its `#### Verify`. Read them for every build-time decision: the mid-build maintainer decision to add `drop-rule` and `drop-section`, the orchestrator's reading of the §4.1–§4.3 tripwire (both in Phase 3's record), and the new `PRE_IDENTITY` finding kind (Phase 2's). Every phase closed **SHIP-READY** after its review loop. ⚠ **One Phase 4 LOW is deferred to Phase 7:** the example in `src/agents-AUTHORING.md`. **Next: Phase 7, the docs sweep. Phase 8 stays the maintainer's, NOT run.**)*
3. **Re-verify F1–F11 against the live tree** (`### Re-check (2026-09-24)` is the last recorded pass). Grep the quoted text, never the digits: `Section 3.5 echo template`, `proposes for Section 3.5`, `Compose 4-7 sub-sections`, `Common sub-sections: Minimal Changes`, `Function Length / Complexity`, `Section 3 Documentation sub-section`, `"tag_or_label": heading`, `r.get("tag", "")`, `Fixture strategy`, `Real-producer principle`, `forge_check_constitution_drift`, `leaving as-is`, `.devforge/template/.claude/agents`, `[\d]+\.[\d]+(?:\.[\d]+)*`, `- [<rule.tag>] <rule.text>`, `templateDerived`, `WARN-only drift notice`, `Project customizations live in`. ⚠ After a build phase some of these strings are gone by design; zero hits is then the built state, not a regression.
4. **D5 was taken as settled first at the 2026-09-24 close, then D4, D3 and D2**, and the record's **Ordering and conditions** block discharges each condition explicitly — D2's discharge by the orchestrator's reasoning, not the maintainer's. If D2, D3 or D4 is ever re-opened, re-read its condition against D5 before treating it as settled: a blanket close does not discharge a condition, and only the record's explicit discharges count.
5. **Build order:** Phase 1 is independent and may ship alone. Phase 2 before Phase 3; **Phase 3 before Phase 4, without exception**; Phases 2 and 3 before Phase 5; Phase 5 before Phase 6; Phase 7 last, because it records what the others did.
6. **Route every edit through the house flow:**
   - python-engineer → python-reviewer for every code edit — Python (with a test per function, run in the same turn), the drift-check script's shell lines, the `install.sh` and `update.sh` code lines, and the `src/manifest.json` entry; for the shell and manifest lines the reviewer runs the affected install/update path against a scratch target, never a consumer install;
   - instruction-author → instruction-reviewer for every markdown edit and for Phase 7's single `update.sh` comment;
   - `claude-code-guide` for every new Claude-Code-integration fact.
7. **Commit by explicit path, never `git add -A`.** Re-read `git status` first (F8), and touch no other session's plan file.
8. **After each phase, cross-check.** Grep every verb, key, section number and heading touched — `verify-universal-defaults`, `_UNIVERSAL_SECTIONS`, `tag_or_label`, `Section 3.5`, `3.8 Design Fidelity`, `seed-universal` if it exists *(it exists since Phase 3 — added 2026-09-25 at build)* — and fix any dangling reference in the SAME change.
9. **Run Phase 7, then leave Phase 8 to the maintainer.**
10. **Keep the evidence class attached.** Any summary of this plan repeats it: **F1 observed once as a label confusion; F4, F9, F10 and F11 reproduced on 2026-09-24 on a scratch state built through the real CLI (reproductions, not consumer incidents); F2 and F3 found by reading; nothing measured on any consumer.**
