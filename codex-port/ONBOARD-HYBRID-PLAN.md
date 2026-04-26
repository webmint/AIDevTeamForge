# Onboard Hybrid — Implementation Plan

## Lineage

This branch is the third in a parallel-explore family:

- **`feature/onboard-path-b`** — original 49-step Path-B-style design with per-symbol extraction and capability-evidence helpers. Paused at Step 1.1. Preserved as evidence of what was over-scoped before R5 measurement.
- **`feature/onboard-simple`** — Claude-authored simple-prompt approach. R5 Claude validated reference-quality output. Spec works on Claude. Preserved as the Claude-side production spec.
- **`feature/onboard-simple-codex-authored`** — Codex's rewrite of the simple spec. R6 falsified the authorship-bias hypothesis: Codex's executor produced same-shape output regardless of who authored. Preserved as evidence; not a merge candidate.
- **`feature/onboard-hybrid`** (this branch) — synthesizes findings from R1/R5/R6 + both Codex interviews. Implements Codex's own Q10 design recipe as the helper architecture. Single spec, runtime-asymmetric helper enforcement.

Branched from `feature/onboard-simple` to inherit the validated Claude spec as the base. Helper enforcement and verifier upgrades are layered on top.

## What we know empirically (n=2 across 4 cross-runtime measurements)

| Measurement | Spec | Executor | Quality (self-rated) | Mechanism |
|---|---|---|---|---|
| R1 baseline | current main | Claude | low (no specific rating) | LLM-prose, sample-based at scale |
| R1 baseline | current main | Codex | very low | LLM-prose, compound-named features, missed API |
| R5 | Claude-authored simple | Claude | reference quality (Claude rated 7/10) | per-unit subagent dispatch + memory propagation |
| R5 | Claude-authored simple | Codex | 4/10 (Codex self-rated) | self-built generator, mechanical extraction |
| R6 | Codex-authored simple | Codex | 5/10 (Codex self-rated) | self-built generator (more careful), still mechanical |

**Key empirical findings:**

1. Claude side ships fine on simple prompt. R5 Claude output matches reference-quality outputs from prior frameworks (no helper apparatus needed).
2. Codex's executor reaches for tooling regardless of who authored the spec. Spec-level instruction is treated as "context" not "binding."
3. Author-vs-executor asymmetry within the same model: Codex authored a spec mandating per-unit dispatch + per-concern decomposition, then ignored both prescriptions during execution.
4. Memory propagation across runs is a load-bearing mechanism (Claude's R5 inherited bug findings from prior memory.md, propagated as pre-seeded subagent context, re-confirmed by source reading).
5. Per-runtime spec variants don't help — Codex's own variant produced same-shape output as Claude's variant on the Codex executor.

**The conclusion**: spec-engineering alone won't close the Codex-side quality gap. Mechanism-level enforcement is required.

## Design recipe (from Codex's R6 interview Q10)

When asked what would force the prescribed pattern, Codex itself authored the design:

> "To actually produce the prescribed per-concern decomposition, the execution would need hard constraints that remove the attractive shortcut.
>
> - The unit of completion must be 'one concern doc file,' not 'one package doc containing concern sections.'
> - Verification must fail if a concern lacks its own file when the concern is nontrivial.
> - The generator, if any, must emit a doc graph, not a single monolithic index.md.
> - The executor must be forced to use subagents or equivalent isolated passes per unit/concern.
> - Architecture and memory need separate explicit passes with different prompts/rules from package docs.
>
> The key forcing function is a stricter verifier."

Plus four additional mechanism findings from the interviews:

- **Q4 (R6)**: proximity-of-authorship-to-execution increases conformance. Verification rules adjacent to execution prompt outperform rules in referenced files.
- **Q5 (R6)**: per-doc templates need to split by purpose. One template can't serve both architecture-level synthesis and package-level surface enumeration.
- **Q6 (R6)**: memory extraction must be a separate explicit pass with a source-reading mandate. Otherwise the executor's "cheap statements from generated docs" rule produces meta-observations, not project archaeology.
- **Q7 (R6) — the diagnostic articulation**: "two partially coupled control layers... the authored plan and the executed plan can diverge a lot unless something forces conformance."

## Design tenets (carried forward from feature/onboard-simple)

1. **Cover all code at agent-navigation depth.** Every meaningful source folder gets a documentation home. Density target derives from "agent can navigate and decide where to make changes from this doc alone, without opening source for first-pass orientation."
2. **Mirror folder structure.** Source tree → doc tree. No shape selection. No heuristic.
3. **Code blocks lifted from real source.** Every code example has a `<!-- path/file.ext:line-range -->` reference. No invented code.
4. **Boundary surface, not implementation.** Document what crosses module/class/component boundaries. Skip private helpers and bodies.
5. **No bundled pattern assumptions.** `architecture.md` observes the project's actual patterns; spec mandates structure not content.
6. **User-corrigible.** Baseline + Overwrite/Merge/Abort across all `docs/` outputs.
7. **Cross-runtime parity by determinism + helper enforcement.** Mirror-folder is mechanical; helper-API constrains executor orchestration; verifier catches what slips through.

## New tenet introduced by R6 evidence

8. **Helper enforcement as the only orchestration path for Codex.** The helper API exposes only the prescribed verbs (one-doc-file-per-write). Bulk-script-write is unrepresentable in the API surface. This is structural prevention, not post-hoc rejection.

## Resolved design decisions

### H1 — Single spec, runtime-asymmetric helper requirement

**Choice**: ship one spec text (the Claude-authored `feature/onboard-simple` version, lightly amended). Helper invocation is *required* for both runtimes. Claude executes the helper API verbs naturally (one-tool-call-per-doc fits its per-unit subagent dispatch pattern). Codex is *forced* through the same helper API — generator-build is unrepresentable because no helper verb writes docs in bulk.

Rationale: Codex's R6 outcome proved per-runtime spec variants don't help. Single spec + uniform helper requirement is simpler architecturally and tests parity at the mechanism level.

### H2 — Helper API surface (from Codex's Q10)

The helper exposes *only* per-prescribed-verb writes. No bulk-script API. Verbs:

| Verb | Required usage | Forces |
|---|---|---|
| `add-package-doc <unit-name> --content` | Once per package; verifier rejects if any package lacks a doc | Per-unit dispatch (one write event per package) |
| `add-concern-doc <unit-name> <concern> --content` | Required for nontrivial concerns; verifier rejects packages whose detected substantive subfolders lack their own concern files | Per-concern decomposition (closes the R6 collapsed-monolith failure) |
| `add-architecture-doc --content` | Single call. Distinct prompt template (NOT the per-package template). Codex's R5 Q5 finding: forcing same template on architecture distorts content. | Architecture-level synthesis |
| `add-memory-finding --category --unit --observation` | Multiple calls during a separate dedicated source-reading pass. Memory is first-class, not a postscript over generated docs (closes Codex R6 Q6 finding). | Project archaeology over generated-doc summarization |
| `compose-onboard` | Atomic finalization: runs all verifier gates, drops baselines if pass | Single pass/fail outcome |

State file: `.devforge/.onboard-state.json` (atomic write via temp + os.replace). Same pattern as Path B's `detect_report.py`.

### H3 — Verifier upgrades (semantic, not just structural)

Following Codex R5 Q4 finding: structural-only verification missed semantic gaps. The verifier on `compose-onboard` gains:

| Check | Mechanism |
|---|---|
| **Per-package coverage** | Listing-diff: every `packages[]` entry has an `add-package-doc` registration. |
| **Per-concern decomposition** | For each package: detect substantive subfolders (>3 files OR clear architectural role); fail if no `add-concern-doc` registration for each. |
| **Code-block sourcing** | Spot-check 5 random code blocks for `<!-- path/file.ext:line-range -->` reference. Any unsourced block fails. |
| **Code-block COUNT vs reference COUNT** | Self-validation per Claude's R5 Q10. Count fenced code blocks; count reference comments; require equality. Self-report numbers in `compose` output. |
| **Boilerplate-overview detector** | Reject overviews matching template phrases like `is a documentation unit inside`, `feature boundaries, presentation adapters, and supporting domain contracts`. |
| **Principal-type presence** | If a package has a class with `BLoC`/`Service`/`Repository` in name, Types section must include corresponding `<X>State`/`<X>Result`/`<X>Options` interface. Heuristic but catches the R5 Codex `QuoteOwnersState` miss. |
| **Type dedup** | Within a Types section, no two code blocks may share the same exported symbol name. Closes R5 Codex `FooterChargeLine appears twice` failure. |
| **Cross-link existence** | Spot-check 5 random Markdown links resolve to existing files. |
| **Sigil hygiene** | Lifted from current spec. |

### H4 — Spec amendments (close-to-execution placement)

Codex R6 Q4 finding: rules adjacent to execution outperform referenced rules. The spec is adjusted to:

- Move all verifier rules to the prompt section immediately preceding tech-writer dispatch (not in a Section A.4 referenced from elsewhere).
- Place the helper API verb list inline in the subagent prompt template, with explicit per-verb invocation examples.
- Add Claude's Q10 self-validation language: "Before returning, count fenced code blocks AND count `<!-- path:line -->` reference comments. These must equal. Self-report both numbers. If they don't equal, fix and re-count before returning."

### H5 — Memory as first-class pass (not postscript)

Codex R6 Q6 finding: memory got reduced to meta-observations because the executor's actual rule was "infer from docs already generated." Fix:

- Memory extraction is a **separate explicit pass** dispatched after all package/concern/architecture docs are written.
- The memory pass prompt explicitly mandates fresh source reading: "You are now reading source for archaeology. Do not summarize the docs you just wrote. Identify project-specific findings: latent bugs, naming hazards, V1/V2 coexistence, dependency gotchas, performance warnings."
- Helper rejects `add-memory-finding` calls whose evidence string matches text already in any `docs/<...>` file (heuristic: discourages summarization-of-generated-content).

### H6 — Architecture as first-class pass (not template-reused)

Codex R6 Q5 finding: forcing per-package template on architecture.md distorted content (`ILanguageEntry` chosen as principal type because parser scanned `pkg-cse-types` first). Fix:

- `add-architecture-doc` has its OWN prompt template, distinct from per-package.
- Architecture template required sections: Architecture overview / Module-package structure / Patterns (multi-pattern when present, scoped) / Conventions / Cross-cutting concerns / Dependency direction rules / Dependency overview (Mermaid graph encouraged).
- Architecture template explicitly does NOT have a "Main Exports" section. That avoids the package.json-script-dump failure.

### H7 — Memory propagation as documented mechanism

Claude R5 Q3 finding: 4 QuoteBLoC bug catches were inherited from prior memory.md, not single-shot detection. Memory propagation across runs is load-bearing — first run's findings become next run's pre-seeded context.

Fix: spec explicitly documents this. The orchestrator's subagent prompt template includes scoped pre-seeded findings from `.devforge/memory.md` — for unit X, include any memory entries that mention X. Subagent receives priors and re-verifies via source reading. Quality compounds across runs.

### H8 — Per-runtime parity testing protocol

R7 measurement when implementation completes:
- R7-Claude on `~/Projects/testParity/` with hybrid spec + helper.
- R7-Codex on `~/Projects/testParity-codex/` with hybrid spec + helper.

Pass criteria:
- Both runtimes produce: per-package docs + per-concern docs (decomposed) + architecture.md (rich, multi-pattern) + memory.md (project archaeology, not meta-observations).
- Codex's R7 quality at or near R5 Claude (~7/10 self-rated equivalent).
- No regression on Claude side from R5 Claude.

If R7-Codex hits 7+/10, hybrid is validated and merged to `feature/codex-support`. If not, theory needs another iteration.

## Atomic step plan (~12-15 steps)

Smaller than original Path B's 49 steps because Codex's Q10 + interviews resolved most design uncertainty.

### Phase 0 — Pre-work *(complete via this plan)*
- 0.1 ✓ Branch cut from `feature/onboard-simple` (preserves Claude-validated spec base).
- 0.2 ✓ This plan captured.

### Phase 1 — Helper skeleton + state

- 1.1 Create `scripts/lib/onboard_helper.py` — argparse skeleton with all 5 subcommands (set/add-package-doc/add-concern-doc/add-architecture-doc/add-memory-finding/compose-onboard). Stubs only.
- 1.2 Implement state RW (`.devforge/.onboard-state.json`, atomic temp+replace).
- 1.3 Implement basic per-verb registration (no validation yet). Store registrations in state file.
- 1.4 POSIX launcher `scripts/lib/onboard_helper` (mirror `scripts/lib/detect_report` pattern).
- 1.5 Implement `compose-onboard` (no validation yet) — atomic write of all registered docs to `docs/<...>/<file>.md`.

### Phase 2 — Validation gates (the forcing function)

- 2.1 Per-package coverage check: every `packages[]` entry has `add-package-doc` call.
- 2.2 Per-concern decomposition check: detect substantive subfolders (file count + concern-name heuristic); fail if no concern docs registered.
- 2.3 Code-block sourcing + count-equality self-validation. Helper requires `block_count` and `ref_count` fields per registration; rejects mismatches.
- 2.4 Boilerplate-overview detector (reject phrases like "is a documentation unit", "feature boundaries, presentation adapters").
- 2.5 Principal-type presence heuristic (BLoC/Service/Repository → corresponding State/Result/Options expected in Types).
- 2.6 Type dedup within a doc.
- 2.7 Cross-link existence + sigil hygiene (lift from current spec).

### Phase 3 — Spec amendments

- 3.1 Amend `src/commands/onboard/main.md` to mandate helper invocation as the only doc-write path. Explicit verb list inline. Per-verb invocation examples.
- 3.2 Add Q10 counting-self-validation language to subagent prompt template.
- 3.3 Split per-doc templates: per-package vs architecture vs memory. Each gets its own subagent prompt.
- 3.4 Document memory-as-first-class-pass and pre-seed-findings-into-subagent-prompts mechanism.

### Phase 4 — install.sh + generator

- 4.1 Extend install.sh helper-copy block to include `onboard_helper*`.
- 4.2 Confirm Python 3 preflight covers new helper (no new check needed).
- 4.3 Scratch install validation.

### Phase 5 — R7 measurement

- 5.1 Reinstall testParity (Claude) from this branch; run `/onboard`; capture transcript + outputs.
- 5.2 Reinstall testParity-codex (Codex) from this branch; run `$onboard`; capture transcript + outputs.
- 5.3 Compare R7-Claude vs R7-Codex vs reference outputs (R5 Claude target, prior framework reference).
- 5.4 Append R7 section to `codex-port/phase-R/parity-findings.md`.

### Phase 6 — Decision gate

- 6.1 Score against ship criteria (per-package coverage on both / per-concern decomposition on both / architecture.md substantive on both / memory.md archaeology on both / no Claude regression).
- 6.2 If pass: merge `feature/onboard-hybrid` → `feature/codex-support`. Archive `feature/onboard-path-b`, `feature/onboard-simple-codex-authored` as evidence-only branches.
- 6.3 If fail: document gap; iterate on helper or spec; re-run R7.

**Total: ~14 atomic steps across 6 phases.**

## Open work TODOs (deferred)

- [ ] **`/update-docs` command (or equivalent)** — incremental doc updates as code evolves; greenfield doc lifecycle. Out of scope for hybrid; planned next.
- [ ] **Downstream command wiring** (plan, specify, execute-task, breakdown, verify) — still in `_pending/`; inheritance of locked terminology + reading-by-command pattern when promoted. Out of scope.
- [ ] **Article from accumulated material** — three Obsidian notes + interview key points + spec comparison form publication-ready substrate. Q7 quote from Codex R6 is the centerpiece. Independent of Forge implementation.

## Pickup instructions for fresh session

1. Confirm branch `feature/onboard-hybrid` is checked out.
2. Read this plan in full + cross-read:
   - `codex-port/ONBOARD-IMPLEMENTATION.md` (path-b branch — context for what was over-scoped).
   - `codex-port/ONBOARD-SIMPLE-PLAN.md` (simple branch — context for what worked on Claude).
   - Obsidian theory note (full theory + R6 outcome).
   - Obsidian Codex interviews note (mechanism findings).
3. Identify next atomic step by `git log` + step-ID search.
4. Build helper, amend spec, run R7. Approval gate at every step.

## Status

Plan captured. Branch ready. Helper architecture specified by Codex itself (Q10 from R6 interview). Spec base inherited from validated `feature/onboard-simple`. Implementation budget: ~14 atomic steps. R7 is the validation gate; if Codex-side hits 7+/10 quality, hybrid is the answer. If not, iterate.
