# COMMAND-VERIFY-GATES-PLAN

**Status**: Drafted 2026-05-17.
**Branch**: `develop-2.0-init`
**Driver**: Facts-first audit (see conversation 2026-05-17) found 3 done-commands whose `## Verify` blocks either don't exist or are prose-imperative rather than fenced shell calls. Convert each to an executable assertion so re-runs and model upgrades cannot reinterpret the post-condition.

## Context for next session

The 4-command sequence (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`) shipped 2026-05-11 (see `project_4command_architecture_pivot.md` memory). Two other commands (`/specify`, `/discover`, `/research`) shipped alongside. Audit comparing every command's verification gate:

| Command | Verify form | Status |
|---|---|---|
| init-forge | step 6 has `test -f`; no per-state `verify` subcommand | partial — Finding 2 |
| generate-docs | Phase 5 prose ("walk on-disk + run `validate-doc`") | prose — Finding 1 |
| configure | `configure_helper verify` shell ✓ | OK |
| constitute | `constitute_helper verify` + `validate` + `summary` shell ✓ | OK |
| discover | `discover_helper verify` shell ✓ | OK |
| specify | 4 verifiers in Step 4.9 (pre-render); no post-render gate | partial — Finding 3 |
| research | `research_helper verify` shell ✓ | OK |

Three findings → three steps below. Each step is independently verifiable + ships with its own helper subcommand test. Order matters: Step 1 (generate-docs) > Step 2 (init-forge) > Step 3 (specify) by impact severity (medium / medium / low), but no inter-step dependency — can land in any order.

Cross-cutting discipline (apply to every step):
- **Test-first** per `feedback_test_first_python_helpers.md` — every new helper subcommand gets a test written + run in the same turn; integration test round-trips via real producer where possible.
- **Cross-check after every change** per `feedback_cross_check_after_every_change.md` — grep for the new verb name across `src/`, `tests/`, `scripts/`, `*.md`; any dangling reference is part of the same change to fix.
- **Sentence-level hallucination check** per `feedback_sentence_level_hallucination_check_specs.md` — every sentence added to a command spec must be verifiable now / mechanically true.
- **Helper-owns-shape** per `feedback_helper_owns_shape_principle.md` — verifier output (stderr enumerated violations, exit code semantics) lives in the helper; command spec only references the verb.
- **Emitter cross-check** per `feedback_emitter_promoted_cross_check.md` — `scripts/emitters/claude.py` does NOT auto-discover; verify if any new helper file is referenced (none expected — all changes are new verbs on existing helpers).

---

## Step 1 — Add `generate_docs_helper verify-all`

**Severity**: medium. **Owner**: python-engineer + instruction-author.

### Why

`src/commands/generate-docs/main.md:573-577` Phase 5 is prose: *"For each rendered doc — concern AND package tier — walk the on-disk file and run `validate-doc` once more"*. The orchestrator is left to compose the per-doc loop from prose. Per-doc `validate-doc` calls in Phases 2.5 / 3.2 / 3.3 are shell, but the aggregator pass at Phase 5 isn't. This is exactly the article's failure mode (spec drift across model versions reinterpreting the loop).

### Files

- `src/devforge/lib/_generate_docs/_cli.py` — register `verify-all` subcommand (no flags).
- `src/devforge/lib/_generate_docs/` — add `_verify_all.py` with `cmd_verify_all` function that:
  1. Reads `.devforge/concerns.json` + `.devforge/packages.json` (state files; verify exact names via current helper code).
  2. Iterates every recorded doc path (concern tier + package tier).
  3. Invokes the existing `cmd_validate_doc` per path (re-use, don't duplicate logic).
  4. Aggregates: exit 0 if every doc passes; exit 2 with stderr enumerating per-path violations otherwise.
- `tests/lib/test_generate_docs_helper.py` — new test cases:
  - Happy path: 2 concerns + 1 package, all valid → exit 0, empty stderr.
  - Failure path: 1 concern with broken structure → exit 2, stderr cites the path + violation.
  - Empty state (no concerns or packages recorded) → exit 0 (vacuous truth).
- `src/commands/generate-docs/main.md:573-577` — replace prose body with:
  ```bash
  ./.devforge/lib/generate_docs_helper verify-all
  ```
  Add 1-line semantic: "Exit 0 = every rendered concern + package doc passes `validate-doc`. Exit 2 = stderr enumerates failures; surface verbatim + STOP (the user re-runs the failed concern / package phase before continuing to Phase 6 Report)."

### Verify

```bash
pytest tests/lib/test_generate_docs_helper.py::test_verify_all -v
./.devforge/lib/generate_docs_helper verify-all --help  # subcommand registered
grep -n "verify-all" src/commands/generate-docs/main.md  # spec updated
```

Integration: run `/generate-docs` end-to-end on testForge20 (or a clean fixture) after Phase 4 completion; Phase 5 invocation must exit 0 with all docs valid.

---

## Step 2 — Add `init_helper verify` + Step 7 in `/init-forge`

**Severity**: medium. **Owner**: python-engineer + instruction-author.

### Why

Every other command in the 4-command sequence + every command alongside (configure, constitute, discover, research, specify) exposes a `<helper> verify` subcommand. init-forge has only `summary` (read-only render) + a step-6 `test -f` for the structural index. No state-integrity gate against `.devforge/init.yaml`.

init-forge is the **first** command — state leaks downstream into configure → constitute → docs. By-eye summary inspection at Step 5 is prose-verify (the same failure mode as Finding 1).

### Files

- `src/devforge/lib/init_helper.py` — register `verify` subcommand. Invariants to cross-check:
  - `workspace_mode` ∈ closed enum.
  - `project_root` non-empty + path exists.
  - `project_state` ∈ `{empty, brownfield}`.
  - `default_branch` non-empty.
  - `packages_detected` is a list; if any manifest exists under `project_root`, list is non-empty (anti-corruption check: walk a small fixed set of manifest filenames at depth ≤2 under `project_root`; if any found, the list must contain ≥1 entry).
  - `.devforge/index.json` + `docs/structure.md` both exist (re-asserts step 6 from a separate verb).
  - Exit 0 = pass; exit 2 = stderr enumerates violations.
- `tests/lib/test_init_helper.py` — add:
  - Happy path: all fields populated, both index artifacts exist → exit 0.
  - Each failure path enumerated above → exit 2 with stderr containing the violation key.
- `src/commands/init-forge/main.md` — add new section before Closing:
  ```markdown
  ## Step 7: Verify

  ```bash
  ./.devforge/lib/init_helper verify
  ```

  Cross-checks `.devforge/init.yaml` + `.devforge/index.json` + `docs/structure.md`: required fields populated, `packages_detected` consistent with on-disk manifests, both index artifacts present. Exit 0 = pass; exit 2 = stderr enumerates violations. On exit 2, surface stderr verbatim and re-run the corresponding setter (`set-workspace-mode` / `set-project-root` / etc.) before re-attempting; if `packages_detected` is the issue, re-walk Step 4.
  ```

### Verify

```bash
pytest tests/lib/test_init_helper.py::test_verify -v
./.devforge/lib/init_helper verify --help
grep -n "Step 7" src/commands/init-forge/main.md
```

Integration: run `/init-forge` on testForge20 from scratch; Step 7 must exit 0. Mutate `.devforge/init.yaml` to remove `default_branch` (or similar); Step 7 must exit 2 with the field name on stderr.

---

## Step 3 — Add `specify_helper verify-rendered` + amend Step 4.10

**Severity**: low. **Owner**: python-engineer + instruction-author.

### Why

`src/commands/specify/main.md:600-609` Step 4.9 runs 4 verifiers (`verify-coverage`, `verify-ac-subsection-coverage`, `verify-ac-shape`, `verify-numerical-consistency`) **before** Step 4.10 render. State JSON is verified; the rendered `specs/<NNN>-<feature-name>/spec.md` on disk is not re-checked. If `Write` is partial (interrupted, wrong path, clobbered by editor), no detection.

Low blast-radius (helper render is deterministic, Write is reliable), but the fact-style fix is one shell call.

### Files

- `src/devforge/lib/specify_helper.py` — register `verify-rendered` subcommand with `--path <spec.md>`. Logic:
  1. Read `--path` bytes.
  2. Invoke the existing `render` codepath to produce canonical bytes from current state.
  3. Compare via **canonical-form normalization** (not raw byte-identity — closes Risk 1 from 2026-05-17 audit):

     ```python
     def _canonicalize(b: bytes) -> bytes:
         text = b.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
         text = "\n".join(line.rstrip() for line in text.split("\n"))
         text = text.rstrip("\n") + "\n"
         return text.encode("utf-8")

     canonical_disk = _canonicalize(disk_bytes)
     canonical_rendered = _canonicalize(rendered_bytes)
     if canonical_disk != canonical_rendered:
         # exit 2 — emit divergence info on canonical forms
     ```

     Rationale: raw byte-identity is brittle — editors silently normalize line endings (CRLF→LF), add/strip trailing newlines, strip trailing whitespace. Any such normalization between `render → Write` and `verify-rendered` read = false positive. Canonical-form tolerates cosmetic editor mutations + catches real content divergence (added/removed lines, character changes).

  4. Exit 0 if canonical bytes match; exit 2 with single-line stderr citing divergence (byte-count diff + first divergent line, computed on canonical forms, NOT raw bytes).

  5. **Precondition: render determinism test** must pass before shipping verify-rendered:

     ```python
     def test_render_is_deterministic():
         state = load_fixture_state()
         b1 = render(state)
         b2 = render(state)
         assert b1 == b2, (
             "specify_helper.render is non-deterministic. "
             "Fix render (strip clock / env / cwd / random reads) "
             "BEFORE shipping verify-rendered gate — gate is meaningless otherwise."
         )
     ```

     If render reads clock / env / cwd / random anywhere, fix render FIRST. The gate's correctness depends on render determinism — non-deterministic render = false-positive drift on every invocation.
- `tests/lib/test_specify_helper.py` — add:
  - **`test_render_is_deterministic`** (precondition gate — must pass FIRST): two render calls on identical state produce byte-identical output.
  - **Happy path**: render → write → verify-rendered → exit 0.
  - **Tamper path**: render → write → mutate the written file (append a stray byte / change a character mid-line) → verify-rendered → exit 2.
  - **Cosmetic-noise tolerance**: render → write → re-write with CRLF line endings → verify-rendered exits 0 (canonical-form correctly tolerates).
  - **Trailing-whitespace tolerance**: render → write → append two spaces to end of a line → verify-rendered exits 0.
  - **Missing-file path**: `--path` points at non-existent file → exit 2 with clear stderr.
- `src/commands/specify/main.md` — append to Step 4.10 (after the `Write` invocation):
  ```bash
  ./.devforge/lib/specify_helper verify-rendered --path "specs/<NNN>-<feature-name>/spec.md"
  ```
  Add semantic: "Exit 0 = on-disk file matches helper render in canonical form (LF line endings, no trailing whitespace, single trailing newline). Exit 2 = real content drift between rendered + written bytes; re-render + re-write before proceeding to Phase 5. Cosmetic editor mutations (CRLF, trailing whitespace) are tolerated; content changes are not."

### Verify

```bash
pytest tests/lib/test_specify_helper.py::test_verify_rendered -v
./.devforge/lib/specify_helper verify-rendered --help
grep -n "verify-rendered" src/commands/specify/main.md
```

Integration: run `/specify` for a small fixture feature; Step 4.10 final call must exit 0. Manually append a byte to the written `spec.md`; `verify-rendered` must exit 2.

---

## When resuming work

1. Read this plan top-to-bottom.
2. Check which steps are already on-disk (each adds a helper subcommand registered in argparse; grep is reliable):
   ```bash
   grep -nE '"verify-all"' src/devforge/lib/_generate_docs/_cli.py    # Step 1
   grep -nE 'add_parser\("verify"' src/devforge/lib/init_helper.py    # Step 2
   grep -nE 'add_parser\("verify-rendered"' src/devforge/lib/specify_helper.py  # Step 3
   ```
3. For each unfinished step, dispatch `python-engineer` agent with the brief (helper + tests in one inseparable unit per `feedback_test_first_python_helpers.md`); follow with `python-reviewer`.
4. After helper lands, dispatch `instruction-author` to amend the command spec; follow with `instruction-reviewer` per `feedback_dual_agent_verify_command_statements.md`.
5. End-of-step verify: run the three commands in each step's "### Verify" block; integration run on testForge20 before marking done.
6. After all 3 steps land, run final cross-grep:
   ```bash
   grep -RnE 'verify-all|verify-rendered|init_helper verify' src/ tests/ scripts/
   ```
   Confirm no dangling references and emitter (`scripts/emitters/claude.py`) does not need updates (these are new verbs on existing helpers, not new helper files).

## Out of scope (this plan)

- **Constitution drift detector** (`constitute_helper verify-universal-defaults`) — separate plan: `CONSTITUTION-DRIFT-DETECTOR-PLAN.md`.
- **Strengthening the prose specs themselves** — every command's Phase 0 / preflight prose stays as-is. This plan only converts the gate post-condition.
- **Refactoring discover / research / configure / constitute verify subcommands** — those are already shell-fact; no change needed.
- **Existing consumer projects re-run** — testForge20 will exercise the new verbs naturally on next 4-command re-run; no proactive migration.

## Related plans

- `CONSTITUTION-STRENGTHENING-PLAN.md` — closed; constitution patches applied.
- `CONSTITUTION-DRIFT-DETECTOR-PLAN.md` — sibling plan; constitution-level facts-first work.
- `PLAN-COMMAND-REDESIGN-PLAN.md` — orthogonal; /plan redesign work.
- `RESEARCH-HELPER-API-ENUM-PLAN.md` — orthogonal; research helper API work.
