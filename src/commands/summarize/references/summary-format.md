# summary.md artifact shape

This documents the shape of `<feature_dir>/summary.md`, the artifact `/devforge:summarize` writes (PHASE 4). `<feature_dir>` — here and everywhere else in this document — is the feature directory `/devforge:summarize` resolved at its PHASE 0.1 (see `main.md`) and held for the whole run; the summary is written to that directory plus the filename `summary.md`. Unlike `/devforge:verify`'s report, there is **no `render-report` helper verb** — the orchestrator composes the summary INLINE in PHASE 3 (agent-free, D1) and writes it with the Write tool. This file is **orientation only**, documenting the shape so the orchestrator knows what to produce. Do not treat it as a verbatim fill-in template — the synthesis is human-facing prose, not a mechanical substitution.

## Findings-free + verdict-free — UNLIKE /devforge:verify

This summary contains NO verdict and NO findings. `/devforge:verify` owns the verdict (APPROVED / NEEDS WORK / REJECTED); `/devforge:review` owns findings. `/devforge:summarize` owns the PR-ready narrative. The summary may REFERENCE the verdict `/devforge:verify` already rendered (read from `verification.md`), but it never computes or renders one. Do not add a verdict line, a findings list, or a refutation pass — those belong to `/devforge:verify` and `/devforge:review`.

## Inputs that shape the summary

The orchestrator composes the summary from five inputs captured during the run (see `main.md` PHASE 1–2) — four scratch files written by helper verbs, plus one direct read of the task files:

1. **The change data** (`gather-change-data` → `$WORKDIR/changes.json`) — `files`, `file_count`, `scope_block`, `by_directory`, `insertions`, `deletions`, `stat_summary`, and `source_changes` (non-null in wrapper mode). Drives the Files-changed section.
2. **The verification report** (`read-verification` → `$WORKDIR/verification.json`) — `ac_list` (one dict per AC with `id`, `status`, `evidence`), `verdict`, `path`, and three fields the helper parsed out of `verification.md` for the Not-verified section: `e2e_status` (the status token of `/devforge:verify`'s e2e run, or `null` when that run recorded none), `has_scope_creep_advisory` and `has_leftover_artifacts_advisory` (bools). The `ac_list` status is AUTHORITATIVE — it drives the Acceptance-criteria section and is never re-derived from the spec (D3).
3. **The task completion notes** (`parse-completion-notes` → `$WORKDIR/notes.json`) — a JSON array, one dict per task (`files_changed`, `notes`, `completed_at`, `has_unverified`, …). Drives the Changes section, the Deviations section, and — via `has_unverified` — the Not-verified section.
4. **The plan decisions** (`read-plan-decisions` → `$WORKDIR/decisions.json`) — `decisions` (one dict per decision with `decision`, `chosen`, `rationale`, `rejected`). Drives the Key-decisions section and, with input 5, the Review-guide section.
5. **The task files themselves** — read directly, not through a helper verb: each task's title, and any behavior-changing / behavior-preserving labels its `## Change Details` entries carry (the Two-hats partition `/devforge:breakdown` writes for a mixed task — labels ON the existing `- In <path>:` entries, with **no subheading, no header field and no flag** to search for). `main.md` PHASE 3 owns this read; it reuses the task-file list PHASE 2.2 already assembled. Drives the Review-guide section. There is no scratch file for it — those labels are free-form prose the orchestrator reads and composes from, which is why no verb parses them.

The header's conditional `**Run by**:` line draws on none of these five — `main.md` PHASE 3 owns what composes it and whether it renders at all.

## Skeleton

```markdown
## Feature Summary: [NNN — feature name]
**Run by**: [the name PHASE 3's provenance rule resolved]
_Records who ran the command that created this document; not updated on later edits._

(The two lines under the title are CONDITIONAL — they render together or not
at all, and main.md PHASE 3 owns both the value and the condition. Unlike
every other bracket in this skeleton, that name is not yours to compose. When
PHASE 3's rule resolves no name, omit BOTH lines so that `### What was built`
follows the title directly; never write `unknown`, an empty value, or a
stand-in. The italic line is the bound that ships with the name — fixed text,
reproduced verbatim.)

### What was built

[2-3 sentences in user terms, synthesized from the spec overview + the plan.
Focus on what the user gets, not implementation details.]

### Review guide

[OMIT THIS WHOLE SECTION when there is nothing to orient a reviewer BY — i.e.
decisions.json's `decisions` is empty AND no task file's `## Change Details`
carries a behavior-changing / behavior-preserving label. When present, 3-5 lines
telling a reviewer where to start, which files carry which decision, and which
changes follow mechanically from those decisions:]
- Start with: `path/to/file` — [the decision it carries, from decisions.json]
- [Consequence] — [files that follow mechanically from the above]
- Behavior-preserving: [entries a task labelled behavior-preserving]

(This is orientation, not enforcement. Nothing checks the mapping — see the
Composition rules below.)

### Changes

[One line per task, in user terms — what it accomplished, not the raw files:]
- [Task title] — [1-line what it did]
- ...

### Files changed

[Grouped by directory/area from changes.json's by_directory, with counts:]
- `src/components/` — N file(s)
- `src/utils/` — N file(s)
- `tests/` — N file(s)
[Total: X files changed, Y insertions, Z deletions]

(In wrapper mode, when changes.json.source_changes is non-null, add a parallel
"Source repo changes" grouping for the code repo alongside the wrapper-side
specs/docs changes.)

### Key decisions

[The most important decisions from decisions.json. One line each:]
- [Decision]: [what was chosen and why]
- ...

### Deviations from plan

[OMIT THIS WHOLE SECTION when no task noted a deviation — i.e. no task in
notes.json has a non-empty `notes`. When present, one line per deviating task:]
- [Task title]: [what deviated and why]
- ...

### Acceptance criteria

[Compact checklist. Each AC's status is taken VERBATIM from verification.json's
ac_list (NOT re-derived from the spec). A passed AC ticks `- [x]`; a non-passed
AC is left `- [ ]` and annotated with its status:]
- [x] AC-1: [short label]
- [ ] AC-2: [short label] — PARTIAL

(When verification.md is absent — the read-verification missing-fallback in PHASE
2.1 — replace this section with: "_No verification report found — run `/devforge:verify`
to populate AC status._")

### Not verified

[OMIT THIS WHOLE SECTION when it would be empty — i.e. no task in notes.json has
`has_unverified` true, AND verification.json's `e2e_status` is null or
`e2e-clean`, AND both `has_scope_creep_advisory` and
`has_leftover_artifacts_advisory` are false. When present, one line per surviving
item, each a VERBATIM report of a status already recorded elsewhere — never a
judgment made here:]
- [Task title] — Done-When boxes left unverified by `/devforge:implement`
- E2E run: [the e2e_status value, verbatim — this line ONLY when the value is
  non-null and not `e2e-clean`] — advisory, did not block the verdict
- Scope creep flagged as advisory in verification.md — did not block the verdict
- Leftover artifacts flagged as advisory in verification.md — did not block the verdict

(Non-passed ACs are NOT repeated here — the Acceptance-criteria checklist above
already annotates each one with its status. This section names only what that
checklist does not.)
```

## Composition rules (so the summary reads correctly)

- **Concise** — each section targets 1-5 lines; the summary is a 1-page narrative, not a report.
- **User-facing** — behavior and outcomes, not implementation mechanics.
- **Deduplicate** — group files by area in Files changed rather than listing each.
- **Omit empty sections** — the Deviations, Review-guide and Not-verified sections are each omitted entirely when their own condition in the skeleton above is met. A feature that trips none of the three renders the five unconditional sections (What was built / Changes / Files changed / Key decisions / Acceptance criteria) — the same document this file described before the two new sections existed, which already omitted Deviations in that case.
- **AC status is authoritative** — taken from `verification.md`, never re-derived from the spec (D3).
- **No verdict, no findings** — `/devforge:summarize` narrates; it does not verify or judge.
- **Review guide is 3-5 lines of orientation, grounded ONLY in named inputs** — compose it from `decisions.json`'s `decision` / `chosen` / `rationale`, the behavior-changing / behavior-preserving labels on task `## Change Details` entries, and task titles + `files_changed` from `notes.json`. Draw on nothing else: do not infer a file's importance from its name, its size, or its position in the diff. **The mapping from files to decisions is your judgment over those inputs, and nothing checks it** — the section's claim is orientation for a reader, not a guarantee about the code. Say where to start and why; never state or imply that the guide is complete.
- **Not verified quotes recorded statuses ONLY** — every line reports a value some other command already wrote down: `has_unverified` per task (from `/devforge:implement`'s annotated Done-When boxes), `e2e_status` (rendered only when it is NON-NULL and not `e2e-clean` — an install with no e2e suite and a gate that returned `off` both arrive as null, so null is never rendered and no comparison against `"off"` is written), and the two advisory booleans (from `/devforge:verify`'s own advisory blocks). Quote the status; never re-derive it, never grade it, and never add an item this command decided was unverified. It names only what the Acceptance-criteria checklist does not — non-passed ACs are already annotated there.
