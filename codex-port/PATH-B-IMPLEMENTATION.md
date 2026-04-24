# Path B — Implementation Plan

Companion to `codex-port/PLAN.md` §10. Design rationale lives there; this file is purely the atomic execution plan.

---

## Decision anchors (resolved before writing this plan)

- **§10.2 Python-runtime-dep**: YES. Target machine is required to have Python 3 at wizard-time.
- **Windows**: IN SCOPE. Same shell-environment assumption install.sh already makes (Git Bash or WSL). A POSIX launcher abstracts `python3` / `py -3` / `python` differences.
- **0-runtime-deps positioning tradeoff**: accepted. Structural parity with Codex on Detection Report emit outweighs the "pure-LLM, no-code" framing for this phase of the project.

## How to use this plan

- Steps are atomic: each has an **entry state**, a concrete **action**, a **self-verify** check, and an **approval gate**.
- At every approval gate, I stop and wait for your go/no-go. I do not chain steps without explicit approval.
- Self-verify is run *by me* before handing control back to you. If self-verify fails, I surface the failure and propose a fix; I do not push past a red check.
- Kill-switch: Phase 7 is the §10.6 integration gate. If criteria fail, we abandon the Path B branch; `feature/codex-support` is untouched.

## Architectural alignment notes

- **Source of truth**: `src/commands/setup-wizard/references/detect.md` (spec), `src/commands/setup-wizard/references/questions.md`, `src/commands/setup-wizard/references/populate.md`. All edits flow through the generator pipeline — never edit installed copies directly.
- **New artifacts** (repo root): `scripts/lib/detect_report.py` (composer) + `scripts/lib/detect_report` (POSIX launcher). Matches existing `scripts/` convention.
- **Install-time copy**: `install.sh` must copy `scripts/lib/detect_report*` into the target. Preflight checks Python 3 presence.
- **Runtime handoff**: LLM (Claude Code or Codex CLI) calls the launcher via Bash tool during Phase 1. Composer writes `.devforge/detection_report.yaml`. Phase 2 + Phase 3 read from file, not conversation.
- **Rollback**: branch `feature/codex-port-path-b` is cut from tag `r3-complete-path-a`. Deleting the branch = full revert.

---

## Phase 0 — Pre-work

### Step 0.1 — Create Path B branch
- **Entry**: on `feature/codex-support` at commit `1b925a1` (HEAD); tag `r3-complete-path-a` exists.
- **Action**: `git checkout -b feature/codex-port-path-b r3-complete-path-a`.
- **Self-verify**: `git branch --show-current` reports `feature/codex-port-path-b`; `git log -1 --format=%H` matches the tag's commit.
- **Approval gate**: confirm branch + starting point before any file edits.

### Step 0.2 — Record §10.2 decision in PLAN.md
- **Entry**: Step 0.1 approved.
- **Action**: edit `codex-port/PLAN.md` §10.2 to mark decision YES with date, note Windows-in-scope, note 0-runtime-deps tradeoff accepted; append a one-line pointer to `PATH-B-IMPLEMENTATION.md`.
- **Self-verify**: `grep -n "10.2" codex-port/PLAN.md` shows the updated resolution; `PATH-B-IMPLEMENTATION.md` is referenced.
- **Approval gate**: review the PLAN.md diff.

### Step 0.3 — Layout audit (read-only)
- **Entry**: Step 0.2 approved.
- **Action**: verify presence and current shape of: `src/commands/setup-wizard/references/detect.md`, `.../questions.md`, `.../populate.md`, `install.sh`, `scripts/`. Confirm `.devforge/` is created by current wizard spec (before Path B composer would write into it).
- **Self-verify**: each expected path exists; note the line ranges for each section I'll need to rewrite in Phase 4 and Phase 5.
- **Approval gate**: report findings (any surprises in file layout? any missing `.devforge/` creation to fix first?) before proceeding to write code.

---

## Phase 1 — Python composer + launcher (no validation yet)

Goal: a working CLI that can `set` / `add-package` / `status` / `compose` and emit YAML identical in shape to the current `detect.md` template. Validation is added in Phase 2.

### Step 1.1 — Create `scripts/lib/detect_report.py` CLI skeleton
- **Entry**: Phase 0 complete.
- **Action**: write the file with:
  - `argparse` dispatch for subcommands: `set`, `add-package`, `status`, `compose`.
  - Stubs only; each subcommand prints "not implemented" and exits 2.
  - Stdlib only. Shebang `#!/usr/bin/env python3`.
- **Self-verify**: `python3 scripts/lib/detect_report.py --help` lists all 4 subcommands; each subcommand prints its placeholder.
- **Approval gate**: review skeleton.

### Step 1.2 — Define schema (dataclasses)
- **Entry**: Step 1.1 approved.
- **Action**: add `DetectionReport` and `PackageEntry` dataclasses mirroring the current `detect.md` YAML template fields exactly (same names, same nesting). Include type hints. No validation logic yet.
- **Self-verify**: import the module standalone (`python3 -c "import importlib.util; spec=importlib.util.spec_from_file_location('m','scripts/lib/detect_report.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print(m.DetectionReport, m.PackageEntry)"`) — no error.
- **Approval gate**: review the field list against `detect.md` template for parity before wiring commands to it.

### Step 1.3 — Implement state file RW
- **Entry**: Step 1.2 approved.
- **Action**: helper functions `load_state()` / `save_state()` that read/write `.devforge/.detection-report-state.json`. Create `.devforge/` if missing. JSON schema mirrors dataclasses.
- **Self-verify**: manual test — write empty state, load it, confirm shape; delete state file.
- **Approval gate**: review state file schema.

### Step 1.4 — Implement `set <field> --value <v>`
- **Entry**: Step 1.3 approved.
- **Action**: wire the `set` subcommand to load state, update the named field, save state. No validation — accept any value. Support dotted paths for nested fields (e.g., `runtime_url.source`).
- **Self-verify**: run `set architecture_shape --value layered`; inspect `.devforge/.detection-report-state.json`; confirm value landed.
- **Approval gate**: confirm nested path handling before packages work.

### Step 1.5 — Implement `add-package --...`
- **Entry**: Step 1.4 approved.
- **Action**: wire `add-package` with all fields from §10.3 (path, manifest, language-hint, framework-hint, build-command, type-check-command, lint-command, test-command, command-source). Append to state's `packages[]`.
- **Self-verify**: add 2 packages, inspect state, confirm both present in order added.
- **Approval gate**: confirm arg shape matches planned wizard call-sites in detect.md.

### Step 1.6 — Implement `status`
- **Entry**: Step 1.5 approved.
- **Action**: `status` prints each required top-level field and its set/unset state + current package count. Machine-readable (one field per line, `field: SET|UNSET|<value>`).
- **Self-verify**: run status on a partially-populated state; output matches current state file contents.
- **Approval gate**: confirm output format is consumable by the LLM (compact, scannable).

### Step 1.7 — Implement `compose` (no validation)
- **Entry**: Step 1.6 approved.
- **Action**: `compose` reads state, emits YAML to `.devforge/detection_report.yaml` using a hand-written emitter (no `pyyaml`). Deletes state file on success. YAML shape must be byte-identical (modulo whitespace) to the current `detect.md` template.
- **Self-verify**: populate a synthetic full state (one package), run compose, diff the output against a snapshot of the current `detect.md` template with values substituted. Expect byte-level match on structure.
- **Approval gate**: review the emitted YAML before moving to validation.

### Step 1.8 — POSIX launcher `scripts/lib/detect_report`
- **Entry**: Step 1.7 approved.
- **Action**: write a shell launcher (no extension, `chmod +x`) that picks the first available of `python3`, `py -3`, `python` (verifying `python --version` reports 3.x), then exec's the `.py` with passed args. Fails with a clear message if none found.
- **Self-verify**: `scripts/lib/detect_report --help` works on mac; `PATH=/tmp scripts/lib/detect_report` (no python in PATH) fails with the intended message.
- **Approval gate**: confirm launcher semantics before every downstream step calls it instead of `python3 ...` directly.

---

## Phase 2 — Validation layer

Goal: reject the three concrete failure modes R1-R3 surfaced (Finding 13 hallucinated paths, Finding 21 free-form enums, Finding 23B abbreviated packages[]) plus general schema safety.

### Step 2.1 — Enum validation per field
- **Entry**: Phase 1 complete + approved.
- **Action**: add enum tables for `workspace_mode`, `project_state`, `architecture_shape`, `runtime_url.source`, `command_source`, any other enum-typed fields. `set` rejects non-member values with message naming the allowed set.
- **Self-verify**: `set architecture_shape --value hexagonal-style` fails with allowed list; `set architecture_shape --value hexagonal` succeeds.
- **Approval gate**: review enum tables against `detect.md` schema for completeness.

### Step 2.2 — Required-field tracking
- **Entry**: Step 2.1 approved.
- **Action**: declare required-field set. `compose` refuses and lists missing fields if any required field is UNSET.
- **Self-verify**: empty-state `compose` fails, naming all required fields; fully-set `compose` succeeds.
- **Approval gate**: confirm the required-field list.

### Step 2.3 — Null-with-reason enforcement
- **Entry**: Step 2.2 approved.
- **Action**: for fields that may be null (e.g., `runtime_url`), `set` requires a companion `--reason <text>` when value is `null`. Record reason in state.
- **Self-verify**: `set runtime_url --value null` fails; `set runtime_url --value null --reason "no web runtime"` succeeds.
- **Approval gate**: confirm reason field lands in emitted YAML (as `runtime_url_null_reason` or similar — decide shape here).

### Step 2.4 — Filesystem existence check on `add-package`
- **Entry**: Step 2.3 approved.
- **Action**: `add-package` stat's both `path` and `path/manifest`. Rejects with clear message if either missing. This is the Finding 13 defense (hallucinated `pkg-test`).
- **Self-verify**: `add-package --path pkg-nonexistent --manifest package.json ...` fails; real package path succeeds.
- **Approval gate**: review error message text for LLM-friendliness.

### Step 2.5 — Package count vs `manifest_count` cross-check at compose
- **Entry**: Step 2.4 approved.
- **Action**: `compose` fails if `len(packages) != manifest_count`. This is the Finding 23B defense (abbreviated `# ... 22 more` case).
- **Self-verify**: set `manifest_count=25`, add 3 packages, compose fails with "3 of 25". Add 22 more, compose succeeds.
- **Approval gate**: confirm `manifest_count` is set separately from `packages[]` (keeps the cross-check meaningful).

### Step 2.6 — Library-category evidence sub-field
- **Entry**: Step 2.5 approved.
- **Action**: per §10.4, library-category fields non-null must carry an `evidence` sub-field populated.
- **Self-verify**: set a library-category without evidence → rejected; with evidence → accepted.
- **Approval gate**: review the list of affected fields.

### Step 2.7 — `runtime_url.source` shape
- **Entry**: Step 2.6 approved.
- **Action**: when `runtime_url.source != "framework-default"`, require a concrete config file path (must exist on disk).
- **Self-verify**: `runtime_url.source="vite.config.ts"` works if file exists; nonexistent file is rejected.
- **Approval gate**: confirm against current detect.md runtime_url rules.

---

## Phase 3 — install.sh preflight + file copy

### Step 3.1 — Python 3 preflight in install.sh
- **Entry**: Phase 2 complete.
- **Action**: at the top of install.sh (after arg parsing, before any file copy), check `command -v python3 || command -v py || command -v python` (and for the last, verify Python 3). Exit 1 with: "AIDevTeamForge wizard requires Python 3. Install Python 3 (python.org / your package manager) and re-run."
- **Self-verify**: install into a scratch dir — success; `PATH=/tmp install.sh /tmp/foo` — fails with the friendly message.
- **Approval gate**: review message wording.

### Step 3.2 — Copy `scripts/lib/detect_report*` into target
- **Entry**: Step 3.1 approved.
- **Action**: extend install.sh copy list to include `scripts/lib/detect_report.py` + `scripts/lib/detect_report` (launcher, mode 755) into `$TARGET_DIR/scripts/lib/`.
- **Self-verify**: fresh install into scratch; both files present; launcher executable; running it from target dir works.
- **Approval gate**: confirm target-side path is what the wizard spec expects to call.

### Step 3.3 — Ensure `.devforge/` exists pre-wizard or is created by composer
- **Entry**: Step 3.2 approved.
- **Action**: confirm state-file write (Step 1.3) creates `.devforge/` if absent; if install.sh already creates `.devforge/`, we rely on that and simplify the python side. Pick ONE place for the mkdir and remove the other.
- **Self-verify**: wipe `.devforge/`, run a `set` call, confirm directory is recreated by whichever owner is canonical.
- **Approval gate**: confirm ownership decision.

---

## Phase 4 — Spec rewrite (detect.md)

### Step 4.1 — Rewrite "Detection Report — Phase 1 output" section in `src/commands/setup-wizard/references/detect.md`
- **Entry**: Phase 3 complete + approved.
- **Action**: replace the fenced YAML template + `<!-- >>> EMIT <<< -->` markers with:
  - A short "CLI protocol" intro: "Phase 1 ends by composing a Detection Report via the `detect_report` helper. Call the helper once per field; call `compose` when done."
  - Per-field instructions ("to set `architecture_shape`, run `scripts/lib/detect_report set architecture_shape --value <one of: ...>`").
  - Per-package instructions ("for each detected package, run `scripts/lib/detect_report add-package ...`").
  - Explicit `status` + `compose` calls at Phase 1 end.
- **Self-verify**: grep for residual `<!-- >>> EMIT <<< -->` in src — none. Grep for `detect_report` — appears at expected call-sites.
- **Approval gate**: review rewritten section against the composer's actual CLI shape.

### Step 4.2 — Keep schema as human-readable reference below protocol
- **Entry**: Step 4.1 approved.
- **Action**: keep a "Schema reference" subsection documenting each field name, type, enum values — but as prose documentation, not as an emit template. The LLM reads this to know *what* values are valid; the composer enforces at set-time.
- **Self-verify**: the section reads coherently as documentation; no LLM-executable YAML template remains.
- **Approval gate**: confirm the schema reference matches the composer's validation rules.

### Step 4.3 — Remove Phase 2 preflight "look back through conversation" wording
- **Entry**: Step 4.2 approved.
- **Action**: in `src/commands/setup-wizard/references/questions.md` Phase 2 preflight section, replace "look back through conversation history for a fenced YAML block" with "read `.devforge/detection_report.yaml`. If absent, return to detect.md and complete Phase 1."
- **Self-verify**: grep `questions.md` for "look back through" / "conversation history" in preflight — none.
- **Approval gate**: review preflight wording.

### Step 4.4 — Regenerate installed files via generator pipeline
- **Entry**: Steps 4.1-4.3 approved.
- **Action**: run whatever generator invocation the project uses (`scripts/generate.sh` or equivalent — confirm in Step 0.3) to produce installed artifacts from `src/`. If generator is not currently part of the flow (manual install is used), skip and rely on direct install.sh.
- **Self-verify**: installed `detect.md` and `questions.md` reflect the src changes.
- **Approval gate**: review generated output.

---

## Phase 5 — Downstream readers

### Step 5.1 — Update `populate.md` §5.5 to read from file
- **Entry**: Phase 4 complete + approved.
- **Action**: in `src/commands/setup-wizard/references/populate.md` §5.5 (project-config.json population), replace references to "Phase 1 Detection Report (in conversation)" with "read `.devforge/detection_report.yaml`".
- **Self-verify**: grep populate.md for "conversation" references in §5.5 — none. Field mapping from YAML → project-config.json is explicit.
- **Approval gate**: review mapping.

### Step 5.2 — Update any other downstream consumers
- **Entry**: Step 5.1 approved.
- **Action**: grep the setup-wizard spec tree for other references to the Detection Report or Phase 1 emission; update each to file-based reads.
- **Self-verify**: no remaining "fenced YAML block" or "Detection Report in conversation" references in `src/commands/setup-wizard/`.
- **Approval gate**: review grep results.

### Step 5.3 — Regenerate
- **Entry**: Step 5.2 approved.
- **Action**: regenerate installed files.
- **Self-verify**: installed copies match src.
- **Approval gate**: proceed to integration test.

---

## Phase 6 — Integration test (R5 dry run)

This is the evidence collection against §10.6 ship-criteria.

### Step 6.1 — Reinstall Claude test worktree
- **Entry**: Phase 5 complete + approved.
- **Action**: wipe `~/Projects/testParity/` (user action — I'll prepare the exact commands) and fresh-install via `install.sh ~/Projects/testParity/`.
- **Self-verify**: `scripts/lib/detect_report*` present in target; `.devforge/` exists; installed `detect.md` references the helper.
- **Approval gate**: ready to run the wizard.

### Step 6.2 — Run Claude-side wizard (user executes)
- **Entry**: Step 6.1 approved.
- **Action**: I provide the exact prompt; you run `/setup-wizard` in Claude Code in `testParity/`. Capture the full transcript + resulting `.devforge/detection_report.yaml`.
- **Self-verify**: `.devforge/detection_report.yaml` produced; shape matches template; packages[] has 25 entries; no abbreviation.
- **Approval gate**: review YAML before Codex run.

### Step 6.3 — Reinstall Codex test worktree + run wizard
- **Entry**: Step 6.2 approved.
- **Action**: same as 6.1-6.2 but for `~/Projects/testParity-codex/` + Codex CLI.
- **Self-verify**: Codex-side `.devforge/detection_report.yaml` produced. **This is the key Finding 23 closure test.**
- **Approval gate**: if Codex emits the YAML, proceed to diff; if not, stop for diagnosis.

### Step 6.4 — Structural diff the two YAMLs
- **Entry**: Step 6.3 approved.
- **Action**: `diff` the two YAMLs. Expect near-identical structure; value differences are acceptable where evidence differs, but field set must match.
- **Self-verify**: diff report.
- **Approval gate**: review diff.

### Step 6.5 — Downstream parity diff (project-config.json, CLAUDE.md, AGENTS.md)
- **Entry**: Step 6.4 approved.
- **Action**: run the usual post-wizard diffs per `run3-observations.md` methodology.
- **Self-verify**: diff line counts; confirm R3 findings are closed or not regressed.
- **Approval gate**: review full findings scoring.

### Step 6.6 — Latency measurement
- **Entry**: Step 6.5 approved.
- **Action**: compare wizard wall-clock time vs. pre-Path-B R3 baseline. §10.6 criterion: ≤5% increase.
- **Self-verify**: measured delta.
- **Approval gate**: review.

---

## Phase 7 — Ship / kill decision gate (§10.6)

### Step 7.1 — Score against §10.6 criteria
- **Entry**: Phase 6 complete.
- **Action**: produce a scorecard covering each §10.6 bullet:
  - Finding 13 hallucination caught at set-time? (y/n)
  - Finding 23B abbreviation caught at compose? (y/n)
  - Finding 21 free-form enum rejected at set-time? (y/n)
  - Latency ≤5% regression? (y/n)
  - Codex-side Finding 23 closed in R5? (y/n)
- **Self-verify**: scorecard complete with evidence references.
- **Approval gate**: you decide ship or kill.

### Step 7.2 — If SHIP: merge to feature/codex-support
- **Entry**: 7.1 → ship.
- **Action**: merge `feature/codex-port-path-b` into `feature/codex-support`. Update PLAN.md: mark §10 as "shipped", close Finding 23, note any new findings discovered in R5.
- **Self-verify**: merge clean; PLAN.md updated.
- **Approval gate**: final review before merge.

### Step 7.3 — If KILL: document and revert framing
- **Entry**: 7.1 → kill.
- **Action**: leave the Path B branch intact for reference; update PLAN.md §10.7 with concrete Path C framing based on what we learned; close Finding 23 as "Path A ceiling reached; documented limitation."
- **Self-verify**: PLAN.md reflects Path C decision with evidence.
- **Approval gate**: final review.

---

## Step-count summary

- Phase 0: 3 steps
- Phase 1: 8 steps
- Phase 2: 7 steps
- Phase 3: 3 steps
- Phase 4: 4 steps
- Phase 5: 3 steps
- Phase 6: 6 steps
- Phase 7: 3 steps

**Total: 37 atomic steps, 37 approval gates.**

## Pickup instructions for a fresh session

1. Read `codex-port/PLAN.md` §10 (rationale).
2. Read this file (atomic execution plan).
3. Confirm branch `feature/codex-port-path-b` exists and is checked out.
4. Identify the next unapproved step by searching commit history for the step ID (each step lands as its own commit).
5. Never skip an approval gate. If a self-verify fails, stop and surface it.
