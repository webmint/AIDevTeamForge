# 29 — /generate-docs SINGLE-ROOT (standalone non-monorepo) SUPPORT

**Status**: Workstream A SHIPPED 2026-06-21 (working tree, NOT committed). A.1–A.3 done + reviewed; A.4 mechanical smoke passed on mintEnvoy real data, full LLM `/generate-docs` run is user-driven (pending). Workstreams B + C still scoped/pending — B's exact edits and C's command-fate decision must be confirmed against the live tree before execution.

## Workstream A — DONE 2026-06-21 (summary)

A.1 (`_enumerate_concerns` Option-A skip) + A.2 (5 review findings incl. 2 HIGH split/tree-prefix bugs at `_preflight.py:202` + `_concern_input.py:406`) + A.3 helper (`_project_input.py` concern-doc fallback: `_enumerate_concern_docs` + `_read_concern_seed` + shared `_read_seed_doc` refactor + 4 review findings) + A.3 spec (`generate-docs/main.md` Phase 3 single-root skip + Phase 4 fallback note + 4 coherence-finding fixes: Phase 5 validate wording, Phase 6 report conditional, Track-4-Phase-3 disambiguation, `## Packages` populate-from-concerns). Decision recorded: `## Packages` on single-root is POPULATED from concern seeds (navigable), NOT empty.

Tests green via `python3 -m unittest`: test_preflight 24, test_concern_input 19, test_project_input 85, test_project_input_label 20. Monorepo output byte-identical (prefix fixes are no-ops for non-`.` packages). **A.4 real-data smoke**: `generate_docs_helper preflight` against mintEnvoy's real `index.json` returns `[('.','main'),('.','preload'),('.','renderer')]` (3 new concerns) — was `[]` before the fix. Full `/generate-docs` LLM run in the mintEnvoy session remains user-driven (composes actual doc content; same pattern as other plans' e2e gates).

**Not yet done in A**: nothing committed; a full forge test-suite run belongs to the commit gate.

## Context for next session

Discovered while installing the framework into a standalone single-root Electron project (`~/Projects/private/mintEnvoy`). `/init-forge` correctly classified it `brownfield`; `/generate-docs` then produced **zero** concern docs and the project tier hard-blocked. Root cause is structural, not scaffold thinness: `/generate-docs`'s concern enumerator deliberately skips the `.` package, which is correct for monorepos but wrong for standalone single-root projects where `.` IS the only real package.

Ground truth captured at draft time (mintEnvoy `.devforge/index.json`):
- `packages` map = `{".": {...}}` — exactly one package, keyed `.`.
- `project_root` = the project's absolute path (standalone; not wrapper).
- Root `src/` exists with immediate subdirs `main/`, `preload/`, `renderer/` → these are the 3 concerns that SHOULD be enumerated once `.` is no longer skipped.

User intent (stated 2026-06-21): the 2.0 canonical setup flow is `/init-forge → /generate-docs → /configure → /constitute`. The `setup-wizard → constitute → onboard` flow still present in `src/CLAUDE.md:40` is **outdated for 2.0**. `/generate-docs` is expected to run on any non-monorepo that has source (even a bare scaffold).

NOTE — contradiction to resolve in Workstream C: git history shows `setup-wizard` + `onboard` were *recently rebuilt/restored* (`db1bcb3 setup-wizard rebuild: detect.md + helper + 72 tests`, `f6c2557 iteration: restore /onboard helper from vault + scope spec to app-web`), both are in the emitter `_PROMOTED` list (`scripts/emitters/claude.py:51`), and plan `28` still references `/onboard` as live. So "the flow is outdated" is confirmed by the user, but "delete the commands" is NOT yet confirmed — onboard may survive as a standalone existing-project doc tool even if removed from the linear setup flow. Do not delete anything in C without an explicit decision.

## Problem (root cause, verified)

`_enumerate_concerns` in `src/devforge/lib/_generate_docs/_preflight.py` (def at line 47) lists `(package_path, concern)` pairs by walking `<project_root>/<pkg>/src/` for each package key in `index.json`'s `packages` map. At lines 90-91 it skips the root package unconditionally:

```python
for pkg in sorted(packages.keys()):
    if pkg == ".":
        continue
```

The docstring (lines 50-53) states the skip is by design: "Source of packages: index.json's `packages` map (excluding the `.` project-root entry)." This is correct for **monorepos** — `.` is the npm-workspaces orchestration root (a `package.json` with `workspaces`, typically no documentable `src/`). It is wrong for **standalone single-root** projects, where `.` is the sole real package.

Consequence chain for a single-root project (`packages = {"."}`):
1. `_enumerate_concerns` returns `[]` → zero concerns.
2. No package-tier concern docs are produced.
3. Project tier hard-blocks: `_project_input.py:1023-1027` emits "no package overviews found under `<project_root>/docs` …" and returns exit 2.

The `docs/overview.md` + `docs/architecture.md` files present in the target are install-time template stubs containing `{{PROJECT_NAME}}`; they are NOT produced by a `/generate-docs` run and the pipeline cannot fill them in this state.

## Why most downstream code already tolerates `pkg == "."`

Python `pathlib` normalizes a `.` path component away: `project_root / "." / "src"` resolves to `project_root/src`, and `Path("docs") / "." / concern` resolves to `docs/<concern>`. The package-tier consumers all build paths this way:
- `_package_input.py:72,175` — `(project_root / pkg / "src")`
- `_package_input.py:97` — `project_root / _CONCERN_DOCS_RELATIVE / pkg / concern / "index.md"`
- `_package_input.py:137` — `(project_root / pkg)`
- `_diff_concern` (`_preflight.py:140`) — receives `pkg` and passes it to `_walk_concern_subfolder`

So the dominant blocker is the single `continue` at `_preflight.py:91`. The fix is small; the work is in proving it (tests) and confirming the project-tier gate clears.

## Design decision (SETTLED — Option A)

**Skip `.` only when other packages exist.** Confirmed by user 2026-06-21.

```python
non_dot = [p for p in packages if p != "."]
for pkg in sorted(packages.keys()):
    if pkg == "." and non_dot:   # monorepo orchestration root → skip; sole package → keep
        continue
```

- Monorepo: always has ≥1 non-`.` key → root `.` still skipped → **behavior unchanged**.
- Standalone single-root: `packages == {"."}` → `non_dot == []` → `.` enumerated → walks `project_root/src/` → concerns.

Rejected alternatives:
- "Enumerate `.` whenever root `src/` exists" — would wrongly document a monorepo's stray root `src/`; brittle, no clean structural signal.
- Keying off `workspace_mode`/manifest `workspaces` — more parsing, same outcome; `len(non_dot)` is the direct, minimal signal and matches the standalone-vs-monorepo distinction `/init-forge` already draws.

Accepted edge case (document in the docstring): a monorepo that has BOTH sub-packages AND a documentable root `src/` keeps its root `src/` skipped — identical to today's behavior, and workspaces-root-with-real-`src/` is an anti-pattern.

## Workstream A — functional fix (PRIORITY; unblocks single-root installs)

### A.1 — Patch `_enumerate_concerns` + tests (test-first)
Delegate to `python-engineer`: apply Option A to `_preflight.py:90-91`, update the docstring (lines 50-60) to state the new rule + the accepted monorepo-root-src edge case. Write + run tests in the same turn (per test-first discipline), round-tripping a REAL `index.json` produced by the actual indexer — not a hand-authored fixture:
- single-root fixture: `packages == {"."}`, with a `src/` containing ≥2 immediate subdirs → assert enumerator returns one pair per subdir, keyed `.`.
- monorepo fixture: `packages` with `.` + ≥1 non-`.` key → assert root `.` produces NO pairs (unchanged behavior).

**Verify**: both tests pass; full `_generate_docs` test suite green (no regression).

### A.2 — `python-reviewer` pass
Review the A.1 change + tests for edge-case coverage, the path-normalization assumption, and any other `pkg == "."` guard elsewhere in `_generate_docs/` that the same single-root case now reaches.

**Verify**: reviewer returns no blocking findings, or findings are folded back through A.1.

### A.3 — Project tier: tier collision (CONFIRMED 2026-06-21 — needs design decision)

Tracing `_project_input.py` confirmed the project tier does NOT auto-clear — it has a structural collision for single-root:
- Package tier (orchestrator Phase 3, `generate-docs/main.md:279`) writes package overview via `init-doc --target "$P"` → `docs/<P>/overview.md`. For single-root `P == "."` this normalizes to **`docs/overview.md`**.
- Project tier (Phase 4, `generate-docs/main.md:321`) writes to **`docs/overview.md`** + `docs/architecture.md` — "NO `<package>` subdir at this tier".
- Same file. `_enumerate_packages_with_overviews` (`_project_input.py:143`) walks `docs/` for `overview.md`, EXCLUDES `docs/overview.md`, and skips `rel_dir == "."` → returns `[]` for single-root → `cmd_project_input` hard-blocks at `_project_input.py:1023-1027` (exit 2).

The two-tier model assumes package overviews live in `docs/<pkg>/` subdirs distinct from the project overview; single-root (`pkg == "."`) collapses package-path and project-path onto the same file. This is a design fork, not a mechanical fix.

**Options (decision pending):**
1. **Collapse to project-tier-only, seeded from concern docs (RECOMMENDED).** For single-root, skip Phase 3 (package overview/architecture); have Phase 4 / `project-input` seed directly from the concern docs (`docs/<concern>/index.md`) when no package overviews exist. Preserves the project tier's rich extraction (tech stack, key commands, structure tree, entry points, glossary, architecture.md). Resulting `docs/`: `docs/<concern>/index.md` × N + `docs/overview.md` + `docs/architecture.md` + `docs/glossary.md`. Matches `/onboard`'s own "Single-app project → single doc home" prior art. Touches `_project_input.py` (concern-doc fallback in `_enumerate`/seed) + `generate-docs/main.md` (skip Phase 3 / Phase-4-from-concerns branch for single-root).
2. **Keep both tiers, relocate the single-root package overview to a subdir.** Package tier writes to `docs/<project-label>/overview.md` (not `docs/overview.md`); project tier then discovers it and composes `docs/overview.md` from it. Faithful to the two-tier model but needs a project-label for the subdir and diverges the single-root path layout from the concern tier's `docs/<concern>/`.
3. **Skip the project tier entirely for single-root (minimal).** The package overview at `docs/overview.md` + concern docs are the whole set. Least work, but loses ALL project-tier richness (tech stack, structure tree, glossary, architecture.md).

**Verify** (after a direction is chosen): a single-root project runs preflight → package/concern tier → project tier (or the collapsed equivalent) without the exit-2 block and produces a coherent `docs/` set; tests assert the chosen layout, round-tripping real rendered concern docs.

### A.1 + A.2 STATUS: DONE 2026-06-21
`_enumerate_concerns` Option-A fix + the 5 review findings (2 split/tree-prefix HIGH bugs in `_preflight.py:202` + `_concern_input.py:406`, weak monorepo regression test, missing `_diff_concern` pkg="." coverage, `non_dot`→`any()` nit) all landed. `79 passed` in the preflight/concern_input suites; monorepo output byte-identical. The concern + package(-input) tier now handles single-root; only the project tier (A.3) remains.

### A.4 — End-to-end on a real single-root target
Re-install the framework into mintEnvoy (`install.sh "$PWD"` from the target), re-run the index, run `/generate-docs`. Confirm 3 concern docs generated (`main`, `preload`, `renderer`) and the project tier composes.

**Verify**: `docs/` for mintEnvoy contains the 3 concern docs + a composed project-tier doc; no `{{PROJECT_NAME}}` stubs remain unfilled in the generated set.

## Workstream B — fix the stale 2.0 flow in `src/CLAUDE.md` (consumer overlay)

The flow diagram at `src/CLAUDE.md:40` reads `setup-wizard → constitute → onboard → …`. Per 2.0 intent it must read the 4-command chain `/init-forge → /generate-docs → /configure → /constitute`. Line 264 ("docs/ is generated by `/generate-docs` (Plan F)") and the per-command gate text (which already cite the 4-command chain) contradict the diagram — reconcile all of them to one story.

Because `src/CLAUDE.md` is a shipped consumer-overlay instruction file, route the edits through `instruction-author` + `instruction-reviewer` (intra-file consistency) and carry the cross-file precedents (emitter `_PROMOTED`, command catalog entries) into the brief explicitly. Confirm the exact line numbers against the live tree first — they will drift.

**Verify**: `src/CLAUDE.md` flow + the `/onboard` and `/setup-wizard` catalog entries + line 264 tell a single consistent 2.0 story; `instruction-reviewer` returns no contradiction findings.

## Workstream C — fate of `/onboard` + `/setup-wizard` (DECISION NEEDED before any deletion)

The user called the `setup-wizard/onboard` *flow* outdated. That does not by itself authorize deleting the commands, which were recently rebuilt and are still promoted. Two coherent end-states:
1. **Retire fully** — remove from emitter `_PROMOTED` (`scripts/emitters/claude.py:51`), drop from the flow + catalog in `src/CLAUDE.md`, delete `src/commands/{onboard,setup-wizard}/` + their helpers (`onboard_helper`, the setup-wizard helper) + tests, and re-verify install end-to-end. Per `feedback_emitter_promoted_cross_check`, the emitter does not auto-discover — removal must be mirrored there and validated by a real install.
2. **Demote, keep** — remove from the *linear setup flow* but retain `/onboard` as a standalone existing-project doc-bootstrap (and/or `/setup-wizard` as a re-run config tool), updating only the flow prose, not the command set.

Resolve which end-state is intended before touching code. This contradicts the recent rebuild commits, so it needs an explicit confirmation, not an inference.

**Verify**: end-state chosen + recorded here; whichever path, a real `install.sh` into a scratch target succeeds and the resulting `.claude/commands/` matches the intended command set.

## When resuming work

1. Re-confirm every cited line number against the live tree before writing any edit — `_preflight.py:90-91`, the docstring span, `_package_input.py:{72,97,137,175}`, `_project_input.py:1023-1027`, `src/CLAUDE.md:{40,108,119,264}`, `scripts/emitters/claude.py:51`. They drift.
2. Start with Workstream A — it is confirmed and unblocks single-root installs. Honor test-first discipline (function + run-tests in the same turn; round-trip via the real indexer, not hand-authored fixtures).
3. Do Workstream B only after A lands (so the flow prose can state the working single-root path).
4. Do NOT execute Workstream C until the retire-vs-demote decision is explicitly confirmed.
