# 31 — Exclude framework folders from the consumer project's linters/formatters

**Status**: SHIPPED (working tree) 2026-06-22 — built via the agent loop. Helper `src/devforge/lib/_configure/_lint_ignore.py` + `_cmds_lint_ignore.py` + `lint-ignore` verb in `_cli.py`; `/configure` Phase 6 wired (verify→Phase 7); `docs/v2/ARCHITECTURE.md` phase listing updated. 80 lint-ignore tests + 159 `_configure` suite green. python-engineer→python-reviewer (7 findings incl. a HIGH flake8-empty-key corruption + dead-code removal) and instruction-author→instruction-reviewer (4 spec findings) loops both run.

**AS-BUILT corrections to the design below** (the implementation converged on a simpler/better mechanism — the rest of this plan is the pre-build design, kept for rationale):
- **Scoping = config-file PRESENCE, NOT language detection.** `run_lint_ignore` fires each handler purely on whether the tool's config file exists under `install_root` (handler returns `None` when absent). The planned "key off `/configure`'s detected `languages`/`LINT_COMMANDS`" was dropped — config-file presence is the precise, simpler signal (no .rubocop.yml → rubocop no-op). The `detect_languages_from_configure` / lint-command detectors were built then deleted as dead code. KNOWN v1 gap: a tool run via CLI with NO config file (e.g. ruff with zero config) is not detected → not excluded; deferred (would require CREATING a config, too invasive for v1).
- **gofmt / clippy / vale / shellcheck have NO handlers in v1** (dropped from the registry + spec). They have no path-exclusion mechanism, so a "manual instruction" would be noise. The registry's 15 handlers: prettier, eslint, markdownlint(cli+cli2), flake8, biome, ruff, black, isort, mypy, pylint, rustfmt, rubocop, golangci-lint, VS Code, JetBrains.
- **Non-fatal + default-SKIP on ambiguous reply** (writes into the consumer's OWN tooling configs) — contrast prune-agents' default-apply.

**Remaining**: docs propagation (CHANGELOG + DEVELOPMENT-STATUS) + e2e verify on a real JS + Python target (user-driven, like other plans). Original design + open questions preserved below for rationale.

---

(pre-build) **DRAFTED + HARDENED 2026-06-21, design approved.** Decisions locked with the user (scope + location + cross-ecosystem requirement). Hardened via an agent loop: a fact-verifier checked every per-linter ignore mechanism against official docs (corrected biome `files.includes`, golangci-lint v2 `linters.exclusions.paths`, vale=no-config-exclude, black/mypy/pylint=REGEX-not-glob, tomllib read-only→tomlkit) and `instruction-reviewer` verified the framework-internal claims (fixed `LINT_COMMAND`→`LINT_COMMANDS` plural, `/configure` Phase 6 exists → insert before it, added `discover/` to the folder set, flagged pre-emptive-exclude behavior). All findings folded in below.

## Problem

When the framework installs into a target project, the target's OWN tooling lints/formats the framework-installed folders. **The framework is ecosystem-agnostic — it installs into Python, Go, Rust, Ruby, Java, JS/TS, … projects** — so the fix CANNOT be JS-specific. The installed framework folders contain mixed file types that DIFFERENT ecosystems' tools each pick up:

- **`.py`** — `.devforge/lib/*.py` (the framework's helper code). In a Python target, `ruff` / `black` / `flake8` / `isort` / `mypy` / `pylint` would lint and REFORMAT the framework's own helpers — the most damaging case (black rewriting helper code, mypy/ruff erroring on it).
- **`.md`** — everywhere (`.claude/`, `.devforge/`, `specs/`, etc.). Picked up by `prettier` (JS projects), `markdownlint`, `vale`. Prettier MANGLES the `{{PLACEHOLDER}}` templates + helper-owned markdown structure.
- **`.sh`** — `.devforge/templates/git-hooks/*.sh`. Picked up by `shellcheck`.
- **`.json` / `.yaml`** — config/state. Picked up by `prettier`, `biome`, yaml linters.

Verified instance — `~/Projects/private/mintEnvoy` (Electron + React/TS): `.prettierignore` lists only `out/dist/...`, eslint flat-config `ignores` only `node_modules/dist` — neither excludes `.claude/` or `.devforge/`. But the SAME gap exists for ruff/black in a Python target, golangci-lint in a Go target, etc.

User constraints (explicit): (1) the fix must NOT be JS-only — the framework lands in many ecosystems; (2) eslint-only does nothing useful here (framework folders are `.md`/`.py`/`.sh`, which eslint doesn't lint, and modern eslint flat-config has no `.eslintignore`). The solution MUST be a cross-ecosystem detect-and-exclude across whatever toolchain the target actually uses, plus ecosystem-agnostic IDE excludes.

## Decisions (locked)

- **Folders to exclude**: `.claude/`, `.devforge/`, `specs/`, `bugs/`, `research/`, `discover/`, `audits/`. **NOT `docs/`** — `docs/` is the project's own knowledge base and stays lintable/formattable. (`discover/` added per review — `_discover` writes `discover/<date>-<slug>.md` + `.handoff.json` at runtime, parallel to `research/`.)
  - **Pre-emptive excludes**: only `.claude/` + `.devforge/` are placed by `install.sh`. `specs/`, `bugs/`, `research/`, `discover/`, `audits/` are created LAZILY by workflow commands and will NOT exist when `/configure` runs at setup. The exclusion step adds them anyway (idempotent append works on not-yet-existing paths); the dry-run report must label these as pre-emptive (folder absent now, will be created later) so the detector is NOT built to skip absent paths.
- **Where**: `/configure`. Its phase structure (verified `src/commands/configure/main.md`) is: Phase 0 pre-flight → 1 read inputs → 2 compose → 3 bulk-confirm (STOP) → 4 user-only prompts → 5 render-config / 5.2 prune-agents / 5.3 substitute-templates → **6 verify+report** → Closing. Insert the lint-exclusion step as a **new Phase 6 (between 5.3 substitute-templates and the current verify+report, which becomes Phase 7)**. NOT `install.sh` (copy-only) and NOT `/init-forge`. Rationale: `/configure` ALREADY captures the target's languages + `LINT_COMMANDS` / `TYPE_CHECK_COMMANDS` (PLURAL — schema field `lint_commands`/`type_check_commands` in `_configure/_schema.py`; per-package `lint_command` under `PACKAGE_STACKS`) — the exclusion step keys off that detection instead of guessing the ecosystem.
- **Cross-ecosystem, detection-driven** (never single-tool, never JS-only).

## Tool handling — cross-ecosystem detect-and-append REGISTRY

No universal lint-ignore standard exists, and `.gitignore` is honored inconsistently across tools (ruff/black partially respect it; prettier only via `--ignore-path`; eslint flat-config not at all) — so we cannot lean on one mechanism. Instead: a REGISTRY of small per-tool handlers, each declaring (a) how to DETECT the tool in the target (its config file/key), (b) where its ignore lives, (c) the append/merge syntax. Only handlers whose tool is DETECTED fire. Seed with the common linters across ecosystems; the registry is extensible (adding a linter = one handler entry). Leverage `/configure`'s already-detected language set to prioritize which handlers to even check.

Two tiers:

**Tier 1 — ecosystem-agnostic IDE excludes (HIGH value, covers every language's format-on-save + inspection noise in one lever):**
- VS Code: if `.vscode/` present (or behind confirmation), merge framework folders into `.vscode/settings.json` `search.exclude` + `files.watcherExclude` (NOT `files.exclude` — too aggressive, hides from explorer). JSONC-aware merge.
- JetBrains: `.idea` excludes are per-module `.iml` `excludeFolder` and often git-ignored/user-specific — BEST-EFFORT or printed instruction (OQ-1).

**Tier 2 — per-linter ignore handlers (fire only when detected). Config keys VERIFIED against official docs 2026-06-21:**
- **Python** (framework `.py` lives under `.devforge/lib/` — most important target):
  - `ruff` → `[tool.ruff] extend-exclude` (GLOB list) in `pyproject.toml`, or top-level in `ruff.toml`.
  - `black` → `[tool.black] extend-exclude` (single **REGEX** string, `/`-separated) in `pyproject.toml`.
  - `flake8` → `extend-exclude` (comma-separated GLOB) in `.flake8` / `setup.cfg [flake8]` / `tox.ini`. **Does NOT read `pyproject.toml`** natively.
  - `isort` → `[tool.isort] extend_skip_glob` (UNDERSCORED keys in pyproject) in `pyproject.toml`.
  - `mypy` → `[tool.mypy] exclude` (**REGEX**) in `pyproject.toml` / `mypy.ini`.
  - `pylint` → `[tool.pylint.main] ignore-paths` (**REGEX** on full path) in `pyproject.toml` / `.pylintrc`.
- **JS/TS**:
  - `prettier` → `.prettierignore` (gitignore syntax; create if prettier configured but file absent).
  - `eslint` → FORKS on config style (load-bearing detection): LEGACY `.eslintrc*` → append `.eslintignore`; FLAT `eslint.config.{js,mjs,cjs}` (default v9+) → does NOT read `.eslintignore`; emit a printed note (no fragile JS `ignores`-array auto-edit — OQ-2).
  - `biome` → **CORRECTED**: `files.includes` glob array with NEGATION (`"includes": ["**", "!.devforge", ...]`) in `biome.json` (v2+). The old `files.ignore` was removed.
- **Go**: `golangci-lint` → **CORRECTED**: v2 `linters.exclusions.paths` (REGEX) in `.golangci.yml` (v1 `issues.exclude-dirs` / `run.skip-dirs` are removed/deprecated — version-detect if v1 support needed). `gofmt` has NO ignore (best-effort — see below).
- **Rust**: `rustfmt` → `ignore = [...]` (GITIGNORE-format paths) in `rustfmt.toml`. `clippy` → no path-ignore (best-effort).
- **Ruby**: `rubocop` → `AllCops/Exclude` (GLOB list) in `.rubocop.yml`.
- **Markdown/prose**: `markdownlint` → FORKS on CLI: `markdownlint-cli` reads `.markdownlintignore` (gitignore syntax); `markdownlint-cli2` uses `ignores` (glob array) in `.markdownlint-cli2.{jsonc,yaml,…}`. `vale` → **no config exclude key** (best-effort).
- **Shell**: `shellcheck` → no path-ignore (best-effort; relevant for `.devforge/templates/git-hooks/*.sh`).

**STDLIB-ONLY constraint (verified — reshapes the registry into auto vs manual-instruction tiers):** framework helpers run on the target with bare `python3` (3.8+), no pip install, no third-party libs. The in-house `_configure/_yaml.py` is CLOSED-SHAPE for `configure.yaml` only — NOT a general YAML parser. Consequences for write-handlers:
- **AUTO (stdlib-safe write):** gitignore-syntax line-append (`.prettierignore` [create-if-absent], legacy `.eslintignore`, `.markdownlintignore`); INI via `configparser` (`.flake8` / `setup.cfg [flake8]` / `tox.ini`); JSON via stdlib `json` (`biome.json`, `.vscode/settings.json` — but `.vscode` is JSONC: attempt parse, on failure fall to manual-instruction, never corrupt).
- **TOML (`pyproject.toml`, `ruff.toml`, `rustfmt.toml`):** no stdlib writer. AUTO only the clean case — append a fresh `[tool.X]` block when the table is ABSENT. Table-present sub-cases: do a targeted text edit ONLY if test-proven non-corrupting (else manual-instruction). Tests must cover table-absent / table-present-key-absent / key-present-pattern-absent / pattern-present(idempotent).
- **External YAML (`.golangci.yml`, `.rubocop.yml`):** no stdlib YAML writer + `_yaml.py` won't generalize → **manual-instruction only** in v1.
- **MANUAL-INSTRUCTION (printed, never edited):** external YAML above, eslint-flat, gofmt, clippy, vale, shellcheck, JetBrains. The dry-run report tags each entry `auto` vs `manual` so the bulk-confirm echo shows the user exactly what gets written vs what they must hand-add.

**Format nuances (carry into the handlers):**
- GLOB-vs-REGEX matters: `black`, `mypy`, `pylint` take a REGEX — the folder name must be regex-anchored/escaped (e.g. `(^|/)\.devforge/`), not dropped in as a raw path. ruff/flake8/rubocop/isort take globs.
- File edits: appends to plain ignore files (`.prettierignore`, `.flake8`, `.eslintignore`, `.markdownlintignore`, `.rubocop.yml` list) are idempotent line/entry appends. **TOML edits** (`pyproject.toml`, `ruff.toml`, `rustfmt.toml`) need `tomlkit` for style-preserving writes — **stdlib `tomllib` is READ-ONLY** (Python 3.11+). Decide at build: depend on `tomlkit`, or append a clearly-delimited `[tool.X]` block ONLY when the key/table is absent (OQ-5). YAML edits (`.golangci.yml`, `biome.json`/JSON, VS Code JSONC) are structured merges preserving existing keys.

**Best-effort / not cleanly possible (handle by printed instruction, never a fragile edit):** `gofmt` (no ignore — caller controls paths), `clippy` (only `#[allow]`/`[lints.clippy]`), `vale` (`--glob` CLI only), `shellcheck` (check-code suppression only, not paths), JetBrains `.idea` (`<excludeFolder>` in `.iml` but commonly git-ignored → not shareable).

Helper owns the per-file structure/merge/atomic-write + idempotency; `/configure` orchestrates detection → a single bulk-confirmation echo of the per-tool changes → STOP → `--apply` on confirm (matches `/configure`'s existing confirm-before-apply discipline, e.g. prune-agents). Re-run = no-op.

## Open questions to resolve at build time

1. **JetBrains `.idea`** — attempt the `.iml` `excludeFolder` edit, or printed instruction? (`.idea` often git-ignored; auto-edit may not persist/share.) Lean: printed instruction unless cheap + reliable.
2. **ESLint flat-config** — printed note vs silent skip (auto-editing the JS `ignores` array is fragile). Lean: printed note.
3. **VS Code settings keys** — confirmed: `search.exclude` + `files.watcherExclude`, NOT `files.exclude`.
4. **Registry scope for v1** — ship ALL seed handlers, or only those for `/configure`'s detected language(s) + IDE? Lean: check IDE always + only the detected-ecosystem handlers (don't probe for ruby tools in a Go project), but keep the registry complete so any detected tool is covered.
5. **TOML merge dependency** — editing `pyproject.toml` needs a TOML read/write. Python 3.11+ has `tomllib` (read-only); writing TOML needs care (preserve formatting) — decide: structured-merge via a minimal writer, or append a clearly-delimited `[tool.X]` block only when the key is absent.

## Build steps (agent loop)

1. **Helper** (`python-engineer` + `python-reviewer`, test-first): a `configure_helper` verb (or a new `_configure/_lint_ignore.py` submodule) built as the per-tool REGISTRY described above — each handler: detect → compute framework-folder excludes → idempotent merge/append. A dry-run mode returns a JSON report `{tool, file, action, lines}[]` of what it WOULD change; `--apply` writes. Round-trip tests with realistic fixtures ACROSS ecosystems: a `pyproject.toml` with `[tool.ruff]`/`[tool.black]`; a `.prettierignore` with pre-existing entries + a flat `eslint.config.mjs`; a `.golangci.yml`; a `.rubocop.yml`; a `.vscode/settings.json` with existing keys. Each handler idempotent (re-run = no-op); structured TOML/YAML merges preserve existing keys.
2. **`/configure` wiring** (`instruction-author` + `instruction-reviewer`): add as **Phase 6** (between 5.3 substitute-templates and the current verify+report, which renumbers to Phase 7) — run the detector in dry-run (scoped by `/configure`'s detected language set + always-IDE), show a bulk-confirmation echo of the per-tool changes (incl. pre-emptive-exclude labels), STOP for user confirmation; on a `yes` reply the orchestrator calls the helper with `--apply` (the user replies in prose like Phase 3 — they do NOT type `--apply` themselves). Match `/configure`'s existing Phase 3 / prune-agents stop-discipline + bulk-confirm pattern.
3. **Docs propagation**: CHANGELOG + `src/CLAUDE.md` (if the consumer overlay should mention it) + DEVELOPMENT-STATUS.
4. **Verify**: across ≥2 ecosystems — (a) a JS/TS target (mintEnvoy) → `.prettierignore` gains the framework folders, prettier no longer formats them; (b) a Python target (scratch project with ruff+black) → `pyproject.toml` excludes `.devforge/` so black/ruff skip the framework helpers. Idempotent re-run on each.

## When resuming work

Re-confirm `/configure`'s current phase structure + its bulk-confirm/stop-discipline pattern + how it surfaces the detected language set / `LINT_COMMANDS` / per-package `lint_command` (`src/commands/configure/main.md` + `_configure/_schema.py`) before wiring — the detector should consume that, not re-detect. Build the helper test-first with the cross-ecosystem fixture set. Resolve the 5 open questions at build start. Hold the line on cross-ecosystem: the Python case (`.devforge/lib/*.py` vs ruff/black/mypy) is first-class, not an afterthought — do NOT regress into a JS-only (prettier/eslint) fix.
