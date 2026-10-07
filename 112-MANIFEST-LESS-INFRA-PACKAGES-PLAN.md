# 112 — Manifest-less Infra Packages Plan

**Created**: 2026-09-25
**Status**: **✅ DONE (build) 2026-10-08 — Phase 0 CLOSED 2026-10-07, Phases 1–8 and the post-close amendments BUILT 2026-10-07, and Phase 9 (docs and ledgers) on 2026-10-08. Phase 10, the consumer e2e, is a user-driven HARD GATE, DEFERRED and NOT run, and NOT waived — so "built and build-verified" is the ceiling of every claim this plan makes: built and build-verified, NOT consumer-validated. As of 2026-10-08 the maintainer has not closed the plan.** Commits, in commit order, which is NOT the phase order (`### Post-close amendments — 2026-10-07`, its orchestration note): `d2cbe5b` draft (Phase 0 OPEN) / `6d33d03` Phase 0 close / `d077641` Phase 1 / `37317e7` Phase 2 / `0699d40` Phase 3 / `6a23837` Phase 6 / `1d8e6fb` Phase 4 / `ef98d8c` Phase 7 / `7330117` Phase 7 follow-up / `e863053` post-close amendments A–C recorded / `94dbeff` Phase 3 follow-up (amendment A) / `a9e24ea` Phase 5 / `ce1de16` Phase 8, plus the Phase 9 docs commit; `git log --oneline --grep 'plan-112'` stays the authoritative record. Phase 9 wrote `FINDINGS.md` entries 13 (F15), 14 (F18) and 15 (F20 only — Phase 7 fixed F21) under OQ-3, and this plan's ledger entries in `CHANGELOG.md`, `DEVELOPMENT-STATUS.md` and `PLAN-STATUS-ARCHIVE.md`. *(corrected 2026-10-08 at Phase 9 — until then this line's lead read "Phase 0 CLOSED 2026-10-07; build IN PROGRESS since 2026-10-07 — `git log --oneline --grep 'plan-112'` lists this plan's commits, the build commits' subjects name their phases, and that log, not this line, is the record of what is built; Phase 9 rewrites this line from that log."; Phase 9 rewrote it from that log)* *(corrected 2026-10-07, mid-build — until then this line read "Phase 0 CLOSED 2026-10-07 — NOTHING is built yet; build phases may start, in this plan's build order (`## Phases`)."; the plan's build commits made "NOTHING is built yet" false)* *(corrected 2026-10-07 at the Phase 0 close — until then this line read "Phase 0 OPEN — nothing is ratified and NOTHING is built." and said D1–D5 and OQ-1–OQ-5 awaited the maintainer)* D1 and OQ-1 were closed by explicit pick — D1 (a), both gates, as recommended; OQ-1, which carried no recommendation, answered: only Terraform was present in the observed project — and every other item, D2, D3, D4, D5, OQ-2, OQ-3, OQ-4 and OQ-5, was ratified as recommended by one blanket pick, with no per-item deliberation supplied; nothing was amended or declined. See `### Phase 0 close record`. **After the close, three amendments to D4 were ruled by explicit pick on 2026-10-07, mid-build — see `### Post-close amendments — 2026-10-07`, which overrides the close record where they conflict.** The 2026-09-25 stub carried the problem statement only; the body below — findings, decisions, phases — was drafted 2026-10-07. ⚠ **Evidence class, to be repeated in every summary of this plan: ONE consumer observation, with NO artifact of it in this repo and NOTHING measured; plus one PLANTED codebase-graph probe (F14) and direct helper calls (F12, F15). Every other statement is a read of this tree on 2026-10-07.**

## Problem

A package with no recognized manifest — the evidenced kind is a Terraform root module, a directory of HCL `*.tf` files — is invisible to the setup chain. **Two independent gates stand between such a directory and its generated docs, and they must not be conflated:**

- **Gate 1 — registration, at `/devforge:init-forge` Step 4.** Package discovery is an LLM instruction that registers a directory only when it holds a recognized manifest file (F1). The helper underneath would accept a manifest-less record — `manifest: null` round-trips through `init.yaml` today — and only its setter's required `--manifest` argument blocks it (F2). An unregistered directory has no record in `.devforge/index.json` (F4).
- **Gate 2 — layout, at `/devforge:generate-docs`.** The concern and package tiers document only a `<pkg>/src/<concern>/` layout: a REGISTERED package with no `<pkg>/src/` still gets no concern docs and no package docs (F6), and the `src/` segment is hardcoded at 11 code sites across 8 modules with no single owner (F7).

**Symptoms, per consumer, for a directory Gate 1 keeps out:**

- `.devforge/index.json` and `docs/structure.md` — no record (F4).
- `/devforge:generate-docs` — no concern docs and no package docs (F6).
- `/devforge:configure` — no `PACKAGE_STACKS` record, and the path is absent from `PROJECT_PATHS`, which fills the `{{PROJECT_PATHS}}` placeholder in the agent files (F10).
- `/devforge:constitute` — blind by derivation: it reads the project-tier docs and uses `packages_detected[]` only for two lookups (F11).
- `/devforge:implement` — a touched `*.tf` file matches no package, so `verify-touched` runs the primary-stack fallback — index 0 of the flat command arrays — and nothing that checks Terraform (F12).

⚠ **Fixing Gate 1 alone puts these directories into `index.json` and `/devforge:configure`, but `/devforge:generate-docs` still writes nothing for a registered package that has no `src/` (F6).** The stub's headline symptom — no concern / package docs — needs both gates fixed. Whether this plan takes Gate 2 on is D1.

---

## Origin & evidence

Observed during a full setup-chain run (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) on a wrapper install over an npm-workspaces Node/TypeScript monorepo with Terraform-only packages.

⚠ **Evidence class, to be repeated in every summary of this plan: ONE consumer observation — the run above — of which NO artifact (no `init.yaml`, no `index.json`, no transcript, no generated doc) is in this repo, and NOTHING was measured. Beside it: one PLANTED probe of `codebase-memory-mcp` 0.11.0 in a throwaway scratch repo (F14), and direct helper calls (F12, F15), all run 2026-10-07 by the session that drafted this body. Every other finding below is a read of this tree on 2026-10-07.**

- **The stub's Problem names three kinds** — Terraform-only packages (HCL root modules), SQL procedure trees and workflow-definition YAML packages — **but its Origin names only Terraform-only packages.** Whether the other two kinds were present in the observed project is OQ-1; nothing here treats them as observed.
- ⚠ **What the run observed is the symptom, not Gate 2.** The Terraform directories never reached `index.json`, so `/devforge:generate-docs` never evaluated them: the missing docs observed there are Gate 1's effect. Gate 2 is established by a code read (F6) as the blocker that remains once Gate 1 is fixed. **No summary of this plan may say the run observed Gate 2 or plan 101's residual 12** (D1, Trap 11).
- The layout of the observed project — how many Terraform directories, how deep, whether any held a `src/` — is not recorded anywhere in this repo.
- **Sibling stubs:** plans 113 through 121 each carry the same Origin sentence verbatim (`## Overlap with other plans`).

This repo is public. **This plan names no client, no install, no repo, no ticket id and no session identifier**, and no phase of it may introduce one.

### Verified structure (2026-10-07)

⚠ **Line digits drift — grep the quoted text, never the digits.** This section cites functions and quoted text, not line numbers, on purpose.

**F1 — Registration is an LLM instruction, not code.** `src/commands/init-forge/main.md` `## Step 4: Discover packages` reads: *"Walk the directory tree under `project_root` (depth limit 4 — covers typical monorepo nesting like `apps/<name>/` or `packages/<scope>/<sub>/`) for any standard package-manifest file (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pubspec.yaml`, `Gemfile`, `*.gemspec`, `composer.json`, `mix.exs`, `build.gradle`, `build.gradle.kts`, `pom.xml`, `*.csproj` — use your knowledge of which ecosystem uses which)."* Its skip list is *"`node_modules/`, `vendor/`, `target/`, `build/`, `dist/`, `.venv/`, `venv/`, `__pycache__/`, and any directory whose name starts with `.`"*. The next paragraph: *"If you encounter a file whose ecosystem you cannot confidently identify as a recognized package manifest, skip it rather than calling `add-package` …"*. Then: *"For each manifest, invoke `.devforge/lib/init_helper add-package --path <package-dir-relative-to-project-root> --manifest <filename>`. If no manifests are found …, `packages_detected` stays `[]`."* The file's `## Outputs of this phase` list says `packages_detected` is *"empty `[]` for projects without manifests"*. **So a Terraform root module, a SQL tree or a workflow-YAML directory never gets an `add-package` call.**

**F2 — The helper does not need a manifest; only its setter does.** In `src/devforge/lib/init_helper.py`:
- `cmd_add_package` validates with `_validate_path(args.path, "packages_detected.path")` and `_validate_string(args.manifest, "packages_detected.manifest")`. `_validate_string` rejects only a non-string, an empty or whitespace-only value, and control characters. `_validate_path` additionally rejects absolute paths, drive prefixes and `..` segments; **it checks no existence** (OQ-4).
- `build_parser` registers `sp.add_argument("--manifest", required=True)`. The record appended is `{"path": path, "manifest": args.manifest}`.
- YAML: `_emit_scalar(None)` returns `"null"`; `_parse_scalar_token` returns `None` for `null`; `parse_yaml` accepts ANY key on a record's four-space continuation line. **But `emit_yaml` writes only `path` and `manifest` for each record, so an extra record key is silently dropped on the next re-emit.**
- `_render_summary` formats the raw value — `"- {0}{1}{2}".format(path, padding, manifest)` — so a `None` manifest would print as Python's `None`.
- **Net: `manifest: null` round-trips mechanically today; only the setter blocks it, and only the summary would render it badly.**

**F3 — Three manifest lists disagree, and this plan unifies none of them.** `init_helper._MANIFEST_FILENAMES` carries the comment *"Manifest filenames recognized for the anti-corruption check in `verify`. Closed enum — do not expand at runtime."* It is read only by `_scan_for_manifests`, which `cmd_verify` calls only when `packages_detected` is empty, at depth ≤ 2, with the violation text *"packages_detected: empty but on-disk manifest found at {0}"*. The three lists:
- Step 4's (F1);
- `init_helper._MANIFEST_FILENAMES`: `package.json`, `pyproject.toml`, `setup.py`, `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`, `build.gradle.kts`, `Gemfile`, `composer.json`;
- `index_helper._MANIFEST_REGISTRY`: `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `pom.xml`, `build.gradle`, `build.gradle.kts`, `composer.json`, `Gemfile`, `requirements.txt`, plus a `*.csproj` glob pass in `_detect_manifest`.
Unifying them is plan 118's territory, not this plan's (Trap 2, `## Non-goals`).

**F4 — `index_helper` already handles a registered manifest-less package.** `src/devforge/lib/index_helper.py` `cmd_build_index` iterates only `init_state.get("packages_detected", [])`; **it ignores the `init.yaml` `manifest` value** and re-detects with `_detect_manifest(pkg_dir)`. `_build_package_record` for a directory with no registry manifest yields `"manifest_file": None`, `"scripts": {}`, `"manifest_deps": []`, `"manifest_parse_skipped": False` and the file list. `_list_package_files` drops any directory whose name starts with `.` — so a `.terraform/` directory is not listed — plus `_FILE_WALK_SKIP_DIRS`. `_render_structure_md` renders a missing manifest as `none` (`rec.get("manifest_file") or "none"`). A registered path that does not exist yields a record with `manifest_parse_skipped` set to `True` and the stderr line *"index_helper: package path {0!r} does not exist; skipping"* — not a failure. **So a manifest-less directory's absence from `index.json` is purely Gate 1.**

**F5 — No Python reader branches on the `init.yaml` `manifest` value** (survey of 2026-10-07). Its readers: `init_helper`'s emitter and `summary` (F2); `detect_report.py`, an ORPHANED legacy file whose docstring says *"do NOT extend it"*; `_validators_package.py`'s `_PACKAGES_DETECTED_PATH_RE`, `r"^\s*-\s*path:\s*(.+?)\s*$"`, which matches `- path:` lines only. `configure_helper read-manifests` reads `index.json` records, not `init.yaml`, through `pkg.get("manifest") or pkg.get("manifest_file", "")`, which tolerates `None`. `/devforge:configure` and `/devforge:constitute` receive `packages_detected[]` inside `INIT_JSON`, an LLM input.

**F6 — Gate 2: `/devforge:generate-docs` documents only a `<pkg>/src/<concern>/` layout.** `src/devforge/lib/_generate_docs/_preflight.py` `_enumerate_concerns`: `src_dir = project_root / full_pkg / "src"` then `if not src_dir.is_dir(): continue`; its docstring: *"Packages without a `src/` dir at the resolved location are skipped silently."* The `.` package is skipped whenever any non-`.` package exists (code comment *"monorepo orchestration root → skip"*). `src/commands/generate-docs/main.md` Phase 3: *"Derive the unique package set from preflight's `concerns[*].package`."* **So a package with no `src/` gets no concern docs AND no package docs.** `_package_input.py` `cmd_package_input` prints *"package {pkg!r} has no `src/<concern>/` subdirs at … — verify the package path"* and returns 2. `_validators_decomposition.py` `_check_decomposition`'s docstring: *"No-op when `<project_root>/<package_path>/src/` doesn't exist (some ecosystems use a flat package layout)."*

**F7 — The `src/` segment is hardcoded at 11 code sites across 8 modules, with no single owner.** Under `src/devforge/lib/_generate_docs/`:
- `_preflight.py` — `_enumerate_concerns` (`project_root / full_pkg / "src"`) and `_diff_concern` (`subfolder_prefix = str(PurePosixPath(pkg) / "src" / concern) + "/"`);
- `_concern_input.py` — `_walk_concern_subfolder` (`(project_root / pkg / "src" / concern).resolve()`) and `cmd_concern_input`'s `subfolder_prefix`;
- `_package_input.py` — its OWN `_enumerate_concerns`, a second concern enumeration beside preflight's with a different skip rule (F20) (`(project_root / pkg / "src").resolve()`), and `_collect_src_root_files`, the walk of loose files at `<pkg>/src/`;
- `_setters_concern.py` — `subfolder_prefix = "src/{0}/".format(concern_name)`;
- `_setters_concern_files.py` — `subfolder_prefix = "src/{0}/".format(args.concern)`;
- `_validators_concern.py` — `subfolder_prefix = "src/{0}/".format(concern_name)`;
- `_validate_doc.py` — `basename_attempt = project_root / pkg_part / "src" / concern_part / cite_path`;
- `_validators_decomposition.py` — `src_dir = project_root / package_path / "src"`.
**The mechanical sweep:** `git grep -n -F -e '"src"' -e "'src'" -e 'src/{' -- src/devforge/lib/_generate_docs/` returned 14 lines on 2026-10-07 — the 11 sites above plus three user-facing messages that embed the layout: `_concern_input.py`'s *"(expected <project_root>/{pkg}/src/{concern}/)"*, `_setters_concern.py`'s *"(concern={concern}, subfolder=src/{concern})."* and `_package_input.py`'s `{project_root / pkg / 'src'}`. **A fourth message escapes that pattern:** `_validators_decomposition.py`'s *"{1}/src/; run add-concern --package {1} --concern "*. ⚠ **The three prefix sites (`_setters_concern.py`, `_setters_concern_files.py`, `_validators_concern.py`) filter `index.json`'s package-relative `files[]`; the walk sites read the filesystem directly — two file sets with different skip rules (Trap 10).**

**F8 — Content extraction is language-agnostic.** `_concern_input.py` `_extract_comment_rich_span`'s docstring: *"Always returns top _TOP_LINE_COUNT lines. For each line beyond the top that contains a hazard marker (TODO/FIXME/HACK/WARNING/XXX), include a small context window."* It applies no extension filter. So `.tf`, `.sql` and `.yaml` files inside a concern would get spans; what keeps them out today is the directory layout (F6, F7).

**F9 — Plan 101 recorded Gate 2 and declined it.** `101-NON-WEB-STACK-READINESS-PLAN.md` — `**Status**:` *"✅ DONE (build) 2026-09-23"*, *"CLOSED 2026-09-23 by maintainer directive"* — recorded Gate 2 as **F36**, **residual 12** and **OQ-5** (*"Does this plan take on `/devforge:generate-docs`' `src/` layout (F36)?"*), ratified NO: *"The `<pkg>/src/` gap is layout-generic and observable at the first `/devforge:generate-docs` run, so it is recorded (residual 12), not taken on here."* Residual 12's own trigger reads: *"Phase 5 anchor 5(d), or any `/devforge:generate-docs` run on a consumer with no `<pkg>/src/`."* Plan 101's governing line: *"fix what breaks before it can be observed; record what can be observed as it happens."* Its **F26** reads *"Package selection is operator-correctable"* — `packages_detected` is *"populated by the LLM at `/devforge:init-forge`"*. A case-insensitive grep of plan 101 for `terraform`, `HCL` and `\.tf\b` returns nothing. ⚠ **Plan 101 is CLOSED; no phase of this plan edits it.**

**F10 — `/devforge:configure` has no rule for a package without a manifest.** `src/commands/configure/main.md` Phase 2:
- `PACKAGE_STACKS` records are `{path, language, framework, build_tool, build_command, type_check_command, lint_command, test_command}`, with `path` *"matching `INIT_JSON.packages_detected[].path`"* and `language` *"derived per-package from manifest extension"*. `LANGUAGES` is *"derived per-package from `MANIFESTS_JSON.packages[].manifest`"*.
- `BUILD_COMMANDS`: *"comma-separated list aligned per-package … When a package lacks a `build` script, emit the ecosystem default (`npm run build` for `package.json`, `cargo build` for `Cargo.toml`, etc.)."*
- `test_command`: *"`null` when the package has no test script — do NOT invent an ecosystem-default guess."*
- The `read-manifests` output shape: *"Each entry is `{path, manifest, scripts, dependencies, dev_dependencies, build_tool_hint, framework_hint}`"*. `build_tool_hint` and `framework_hint` are Python-derived (`_configure/_hints.py` `_derive_build_tool_hint`, `_derive_framework_hint`) and both return `None` for empty dependencies — **so a null-manifest package already gets `null` for both, and the existing *"VERBATIM"* rules already make its `framework` and `build_tool` null.** Those two hints are the existing pattern a new derived hint follows.
- `cmd_read_manifests` (`_configure/_cmds_read.py`) spreads each `index.json` record into the package dict it reads, so a record's `files[]` is in reach of a new hint.
- `configure_helper set-package-stacks` (`_configure/_cmds_set.py` `cmd_set_package_stacks`) **requires `language` as a string** — *"set-package-stacks: record {0} missing required field 'language'"* on a missing or null value (D4 (c)).
- `_configure/_render.py` `_build_substitution_map`: `PROJECT_PATHS` is the comma-join of `packages_detected[].path`, and `PACKAGE_STACKS_SECTION` is a table built from `PACKAGE_STACKS`. `{{PROJECT_PATHS}}` appears in 20 agent files under `src/agents/` (grep count, 2026-10-07).

**F11 — `/devforge:constitute`'s blindness is derivative.** It reads the project-tier docs through `constitute_helper read-docs`, and uses `packages_detected[]` only for the `generated_types_dirs` default (`src/commands/constitute/main.md`: *"scan `INIT_JSON.packages_detected[]` for package roots that contain `.d.ts` or generated-types subdirectories"*) and the citation package-name lookup — `_constitute/_validate_metrics.py` `_build_package_name_map`, docstring *"Build {package_name: path} from init.yaml packages_detected list."*, which keys on the path's basename and keeps the LAST record on a basename collision (`result[name] = p`; Trap 14).

**F12 — `/devforge:implement` verify-touched sends a `*.tf` edit to index 0's commands.** `src/devforge/lib/_implement/_cmds_verify.py` `_match_package` is longest-prefix; an unmatched file uses the primary-stack fallback — the module docstring: *"No match → primary-stack fallback (TYPE_CHECK_COMMANDS[0] / LINT_COMMANDS[0] / TEST_COMMANDS[0])"* and *"Non-package files → BUILD_COMMANDS[0]."* Verified 2026-10-07 by a direct call with stacks `[{path: "."}, {path: "packages/api"}]`: `infra/terraform/main.tf` → no match. **So today a `.tf` edit runs index 0's commands and nothing that checks Terraform.** `"N/A"` and absent commands are skipped silently — the docstring: *"\"N/A\" commands are silently skipped (not a failure)."*

**F13 — Agent pruning is NOT a consequence.** `src/agents/devops-engineer.md` carries `applies_to: ["all"]`, and `_configure/_render.py`'s prune rule keeps it — *"\"all\" in applies_to → keep (universal-fit agent)."* — whatever `PROJECT_NATURES` holds. Recorded so nobody re-derives a natures fix.

**F14 — The codebase graph already sees Terraform — a PLANTED probe, not a consumer observation.** On 2026-10-07 the drafting session indexed a throwaway scratch git repo with `codebase-memory-mcp` 0.11.0 — `infra/main.tf` with a variable, a resource and a module block; `infra/net/outputs.tf`; `db/procs/refresh.sql` with a `CREATE PROCEDURE`; `workflows/flow.yaml`; `src/app/a.ts`. HCL blocks became `Class` nodes (`resource.aws_vpc.main_vpc`, `variable.region`, `module.probe_net`, `output.net_probe_out`); the SQL file was indexed as File/Module but reported `parse_partial` at the procedure line, **and the procedure was NOT extracted**; YAML top-level keys became `Variable` nodes. The scratch project was deleted from the graph afterwards. ⚠ **Not tested: any other version, any real project. Nothing in this tree reproduces it.**

**F15 — Out of scope, recorded: a `.` record in `PACKAGE_STACKS` never matches.** `_match_package` matches when `norm_file == norm_pkg or norm_file.startswith(norm_pkg + "/")`; for `path: "."` that requires a `./` prefix, which git-emitted paths do not carry. Verified 2026-10-07 by a direct call: `README.md` → no match. `tests/lib/_implement/test_cmds_verify.py`'s `test_wrapper_command_runs_with_cwd_source_root` uses `"path": "."` and passes either way, because its `TYPE_CHECK_COMMANDS[0]` equals that package's `type_check_command`. **Not this plan's subject — OQ-3.**

**F16 — Index 0 of the four flat command arrays is load-bearing in three helpers.** A grep of `src/devforge/lib/` for the uppercase and lowercase names of `BUILD_COMMANDS` / `TYPE_CHECK_COMMANDS` / `LINT_COMMANDS` / `TEST_COMMANDS` on 2026-10-07 finds every reader that picks ONE entry picking index 0:
- `_implement/_cmds_verify.py` — the primary-stack fallback (F12): `cmd_verify_touched` assigns `primary_type_check = type_check_commands[0] if type_check_commands else None`, and `primary_lint`, `primary_build` and `primary_test` the same way from `LINT_COMMANDS`, `BUILD_COMMANDS` and `TEST_COMMANDS`, each list read the way `type_check_commands = config.get("TYPE_CHECK_COMMANDS") or []` reads its own;
- `_verify/_regression.py` `_get_test_command` — docstring *"Returns None when TEST_COMMANDS is absent, empty, or the first element is \"N/A\" or empty."*;
- `_configure/_validators.py`'s executability probe — *"Only the FIRST entry of each primary array is probed — it is the command that /implement's verify gate will actually run."*
`_configure/_render.py` joins the whole array into `{{BUILD_COMMAND}}` and its siblings (`_SINGULAR_ALIASES`); `_configure/_summary.py`'s only hits — five, case-insensitive — are the four lowercase names `build_commands`, `type_check_commands`, `lint_commands` and `test_commands` as entries of `_SUMMARY_GROUPS`' `"Per-package"` group, plus one comment beside them (*"here, directly after test_commands"*) — it names them nowhere else; `detect_report.py`'s hits are the orphaned file (F5). **Three further files were checked and do NOT index the flat arrays:** `_verify/_e2e.py`, which the grep above reaches, names `TEST_COMMANDS` only in a docstring (*"separate absent-``TEST_COMMANDS`` check"*); `_profile/_segment.py` and `_generate_docs/_project_input.py`, which only a wider case-insensitive grep for `commands` reaches, match it only in unrelated names and their prose (`KNOWN_COMMANDS`; `_extract_key_commands`). **Order:** the configure spec composes the arrays *"aligned per-package"* (F10); `read-manifests` emits packages in `index.json`'s key order; and `build-index` writes `index.json` with `json.dumps(index, indent=2, sort_keys=True)`, so the packages arrive sorted by path — `.` sorting before any path that starts with a letter or digit. **So in a project with no `.` record, a null-manifest package whose path sorts first can take index 0**, and its `N/A` would disable the primary-stack fallback and make the regression gate's test command `None` (D4 (b)).

**F17 — The concern walk does not skip hidden directories.** `_concern_input.py` `_walk_concern_subfolder`'s docstring: *"Hidden dotfile-prefixed dirs are NOT skipped (callers supply --concern explicitly; not a wildcard scan)."* `_enumerate_immediate_dirs`, which feeds the split decision, filters only `_path_contains_trivial_dir`, and `_setters_concern.py`'s `_TRIVIAL_LEAF_DIRS` has no `.terraform`. Today that is harmless — a concern root is a named child of `src/`. **A concern rooted at a package directory (D5 (ii)) would walk `.terraform/` and offer it as a split child** (D5 (iv)).

**F18 — `/devforge:init-forge`'s hand-back arms and `src/CLAUDE.md`'s `### Never` item 7 read differently.** Step 3's option arm: *"If the user hands this choice back to you, take `main`, apply it exactly as above, and name it in Step 5's delegated-values lines."* — the named option on the FIRST hand-back; Step 1 has the same form. Its free-text arm: *"ask it once more, and if the second reply again names no branch, end the turn without invoking `set-default-branch`"*. Step 5's sentence covers *"the user handed its question back to you in Step 1 or Step 3"*. `src/CLAUDE.md` `### Never` item 7: *"At a question that decides what the run does, ask the same question once more, and on a second such reply take the option the command names for that reply"*. **The option arms apply on the first hand-back; item 7 asks once more first.** The difference predates this plan — OQ-3.

**F19 — Out of scope, recorded: a stale 500-file cap at six sites — four in two docs, two in code docstrings.** `src/commands/init-forge/main.md` Step 6: *"walks the source tree (capped at 500 files)"*. `docs/v2/ARCHITECTURE.md`, three hits: *"Walk source tree (capped at 500 files; `files_truncated: true` flag set on overflow)."*; its `_concern_input.py` row: *"(NOT via `index.json`, which caps at 500 files and may truncate large concerns)"*; and its `index_helper` 500-file-cap item: *"Per-package file listings cap at 500"*. A fourth `500` in that file, the `_circuit.py` row's *"invocation-budget exceeded (default 500)"*, is unrelated. **Two code docstrings carry the same stale cap:** `src/devforge/lib/index_helper.py`'s module docstring, *"data: file listings (capped at 500), manifest scripts + dependencies."* — the same docstring says further down *"File listings are capped at 10000 per package"* — and `src/devforge/lib/_generate_docs/_concern_input.py`'s module docstring, *"at 500 entries per package (`files_truncated: true` flag)."* `index_helper.py` holds `_MAX_FILES_PER_PACKAGE = 10000`, with a comment recording the bump from 500 on 2026-05-07. The `done-plans/` files that carry the same 500 text — a grep for `capped at 500` and `500 entries per package` hits `done-plans/CONFIGURE-PLAN.md` and `done-plans/CBM-INTEGRATION-PLAN.md` on 2026-10-07 — are frozen records and are not edited. OQ-3.

**F20 — The two concern enumerations are NOT duplicates: their skip rules differ.** `_package_input.py` `_enumerate_concerns` — docstring *"List direct subdirs of `<project_root>/<pkg>/src/`. Sorted alphabetical."* — skips `name.startswith(".") or name in ("node_modules", "dist", "build", "target")`. `_preflight.py` `_enumerate_concerns` skips `if _path_contains_trivial_dir(entry.name)`, a membership test against `_setters_concern.py`'s `_TRIVIAL_LEAF_DIRS`: `"assets", "dist", "target", "bin", "obj", "node_modules", "__pycache__", ".venv", "vendor", "locales", "__generated__", "fixtures", "i18n", "static", "build"`. **So `src/static/` is a concern for package-input and not for preflight, and a dot-prefixed `src/.x/` is skipped by package-input and enumerated by preflight.** The divergence predates this plan; D5 (i) keeps it unchanged (Trap 15), and OQ-3's F20 / F21 ownership rule names its owner.

**F21 — The concern walk's trivial-leaf filter tests the FULL project-relative path, package components included.** `_concern_input.py` `_walk_concern_subfolder` computes `rel = path.relative_to(project_root).as_posix()` and drops the file `if _path_contains_trivial_dir(rel)`; `_enumerate_immediate_dirs`, which feeds the split decision, tests `_path_contains_trivial_dir(rel + "/x")` on `rel = entry.relative_to(project_root).as_posix()`. `_path_contains_trivial_dir`'s docstring: *"Return True if any path component of rel_path is a trivial-leaf dir."* — it loops over `Path(rel_path).parts`. Preflight's `_enumerate_concerns` tests only `entry.name` (F20), and the three prefix sites test `index.json`'s `files[]`, which `index_helper._list_package_files` makes package-relative (`rel = full.relative_to(pkg_dir)`). ⚠ **Consequence — a code read, NOT observed, and PRE-EXISTING, not caused by this plan:** a `src/`-layout package whose own path holds a trivial name — e.g. `packages/assets` with `src/ui/` — has `ui` enumerated as a concern by preflight while the walk drops every file of it, and of every other concern of that package; `cmd_concern_input` then exits 2 with *"subfolder is empty (or all files are trivial-leaf)"*. **Under D5's fallback the same filter would empty a Terraform package at `envs/static` or `x/fixtures`** — paths D2's verb would propose — **and at `infra/build` or `modules/vendor`**, which the verb skips (`build` is in `NESTED_GIT_SKIP`; `vendor` is D2's further name) and D2's free-text declaration can still register. D5 (v) addresses it (Trap 16), and OQ-3's F20 / F21 ownership rule names its owner under every D1 and D5 outcome.

---

## Overlap with other plans

⚠ **Find a sibling plan by its TITLE, never by its number or a line digit.**

- **Plan 101 — "Non-Web Stack Readiness"** (F9). Its F36 / residual 12 / OQ-5 are this plan's Gate 2, and its F26 names the operator route Gate 1 rests on. **CLOSED; no phase edits it.** Under D1 (a) this plan takes on what plan 101's OQ-5 declined; plan 101's record stays as written, and this plan's ledger entries (Phase 9) say that residual 12 is addressed here.
- **Plan 113 — "Index Skip-List Drops Source Dirs"** (stub). The bare name `target` in the skip sets of `index_helper.py`, `init_helper.py` and `detect_report.py` drops legitimate source directories. **Independent of this plan, but D2's verb reuses `NESTED_GIT_SKIP`, which holds `target`** — whichever of the two lands second aligns the verb's skip set with plan 113's outcome.
- **Plan 116 — "Configure Workspace Commands"** (stub). Composed per-package commands run with cwd = source root and are often not runnable there. It bears on whether a Terraform record could carry commands; **D4 composes none, which sidesteps it.**
- **Plan 118 — "Mechanical Stack Detection"** (stub). The manifest-derived tech stack is thin. A null-manifest package contributes no dependencies to it; **this plan adds only D4's narrow `language_hint`**, which plan 118 may later subsume.
- **Stubs 113 through 121** share this plan's Origin run (`## Origin & evidence`).

---

## Phase 0 — ratification

**Nothing below is ratified.** *(drafting-time text — it applies to D1–D5 and OQ-1–OQ-5 as drafted; Phase 0 closed 2026-10-07 and `### Phase 0 close record` is the ruling)* Each item states its options, a recommendation, the strongest counter-argument — **recorded honestly rather than answered away** — and its consequences for the phases.

### D1 — Scope: which gates this plan fixes

- **(a) Both gates.** Phases 1–5 fix Gate 1; Phases 6–8 fix Gate 2.
- **(b) Gate 1 only.** Phases 6–8 are dropped; Gate 2 stays plan 101's residual 12, and this plan states plainly that a registered manifest-less package still gets no concern or package docs.
- **(c) Gate 1 here, Gate 2 in a new numbered plan.** As (b) in this plan, plus a new stub carrying F6, F7, F8, F17, F20, F21 and D5 as its starting material, numbered by a glob of the repo root at creation.

**RECOMMEND (a).** The stub's headline symptom — no concern / package docs — is not fixed by Gate 1 alone, and that is a code-read certainty (F6), not a prediction. Once Gate 1's phases land, the next `/devforge:generate-docs` run on such a project meets residual 12's own trigger — *"any `/devforge:generate-docs` run on a consumer with no `<pkg>/src/`"* (F9) — on packages this plan registered. Ordering Gate 1's phases first lets them ship whatever happens to Gate 2.

⚠ **Not argued here: that the observed run observed residual 12.** It did not — the directories never reached `index.json` (`## Origin & evidence`). **By plan 101's own line, Gate 2 is still a record-side item;** the case for (a) rests on this plan's own symptom, not on that line.

**Counter-argument, recorded and NOT answered away:** Gate 2 is layout-generic — the helper names flat layouts itself (F6) — so (a) changes `/devforge:generate-docs` for every flat-layout non-`.` package, not for Terraform alone; it touches 11 code sites across 8 modules (F7) and roughly doubles this plan. Plan 101's OQ-5 put the bar plainly: *"A fix is a `/devforge:generate-docs` design change — what a concern IS in a layout with no `src/` — with its own evidence bar, not an edit this plan can carry beside a timeout key and a builder."* **(c) honours that bar; (a) asks the maintainer to accept ONE consumer observation of the symptom as enough.**

**Consequences.** (a): Phases 6–8 run, and Phase 10's docs anchor is a pass criterion. (b): Phases 6–8, D5, OQ-2 and OQ-5 drop; `## Non-goals` gains Gate 2; and Phase 10's docs anchor becomes record-only, expecting no concern or package docs for the registered directories. (c): as (b) in this plan, and Phase 9 also authors the new stub. **Under every outcome, F20 and F21 follow OQ-3's F20 / F21 ownership rule** — its case for each D1 outcome is stated there, not here.

### D2 — Detection: how Step 4 finds manifest-less packages

- **(a) Extend Step 4's LLM walk** with marker signals — e.g. *"a directory holding `*.tf` files"* — the same instruction-only mechanism as the manifest walk (F1).
- **(b) A mechanical candidate verb in `init_helper`** — working name **`detect-manifest-less`** (⚠ a working name, not a ratified one) — in which Python decides, prints candidate paths and writes no state. **Existing precedent in the same helper and the same command:** `find-nested-git`, whose docstring says *"One path per line on stdout. No state is written."*, returns candidates that Step 1.2 puts to the user.
- **(c) Operator declaration only** — Step 4 asks the user to name extra package directories.

**RECOMMEND (b) + (c).** The verb detects the one evidenced kind, Terraform:
- a candidate is a directory holding at least one `*.tf` file;
- per subtree, only the SHALLOWEST such directory is proposed, and the walk does not descend below it — so a root module's nested `modules/` stay inside it;
- it skips hidden directories, `NESTED_GIT_SKIP` and the one further name on Step 4's skip list, `vendor` (F1);
- it walks under the `project_root` recorded in `init.yaml` and counts depth per FILE, as `init_helper._scan_for_manifests` does: that function starts with `return _walk(project_root, 1)`, checks the files of the directory it is walking at the current depth, recurses into each child directory at `current_depth + 1`, and returns `None` once `current_depth > max_depth` — so its docstring's *"Depth 1 = direct child of project_root.  Depth 2 = grandchild."* counts the FILE: a file's depth is its number of path components below `project_root`. A root-level `main.tf` is depth 1; `infra/tf/main.tf` is depth 3. The verb examines `*.tf` files down to depth 4, Step 4's limit (F1), whose own example `packages/<scope>/<sub>/` — a directory 3 components deep — puts its manifest at depth 4 under this counting; so the deepest directory the verb can propose is 3 components below `project_root`, and a `*.tf` file at depth 5 or deeper is never examined;
- it descends through directories that hold no `*.tf` file;
- `.` (the project root) is a candidate exactly when the root holds at least one `*.tf` file — a depth-1 file under the counting above — AND `packages_detected` has no `.` record; the verb then prints `.` only, because every other `*.tf` directory is inside it. When `.` is already registered, root-level `*.tf` files propose nothing and the walk continues descending;
- it proposes no directory that is already a registered package, and none inside one other than `.`;
- its output is one candidate path per line on stdout, sorted by path — the output form of `find-nested-git` (*"One path per line on stdout."*), followed for consistency; this plan detects one kind, so a candidate needs no structured fields.

Step 4 runs the manifest walk first, then the verb, and puts the candidates to the user for confirmation; confirmed ones are registered with D3's record shape. **Phase 4 authors the question text; the option labels are fixed here:** an AskUserQuestion naming the candidates in its question text, with exactly three options, labelled `Register all` (Recommended), `Let me choose which` and `Register none` — the candidate count can exceed four, so the candidates are never the options. The `(Recommended)` suffix is the file's own convention — Step 3's *"- `main` (Recommended)"*, and Step 1's *"- `Standalone project` (Recommended)"* — and Phase 4 writes the three options as a bullet list under the question, the form Steps 1 and 3 use (Step 2 asks nothing). Separately, Step 4 offers a free-text declaration for kinds with no reliable mechanical signal — SQL procedure trees and workflow-definition YAML (YAML files are common across a repo, so a `*.yaml` marker would propose far too much). Its follow-up mirrors Step 3's existing `None of these — let me type the name` arm — **consistency with the file, not invention.** Both questions are skipped when `project_state` is `empty`.

**Hand-back (F18).** RECOMMEND following the active file's own arms: a hand-back at the candidate question registers every detected candidate and is named in Step 5's delegated-values lines, as Step 3 does for `main`; a hand-back at the free-text declaration is asked once more, and a second one registers nothing from it. Step 5's delegated-values sentence, which names Step 1 and Step 3 today, gains Step 4. ⚠ **One arm has no precedent in the file and is flagged as a departure:** a hand-back at the `Let me choose which` prompt is asked once more, and a second one registers every detected candidate, named the same way. Step 3's free-text arm ends the turn instead, because there it has no value to apply on the user's behalf; here the detected candidates are such a value. ⚠ **The alternative — asking the candidate question once more before applying, `### Never` item 7's literal form — is NOT recommended: Step 4 would then diverge from Steps 1 and 3 of the same file.** The file-versus-item-7 difference is OQ-3's to route.

**Edge, recorded:** a candidate that CONTAINS a registered package — a root module directory with a `package.json` package below it — is still proposed. Nesting already occurs (`.` contains every package, and `_match_package` resolves longest-prefix-first, F12); its docs consequence is OQ-5.

**Rejected:** replacing the manifest walk itself with Python — plan 118's territory, and three manifest lists already disagree (F3).

**Counter-argument, recorded:** two discovery mechanisms where there was one; a free-text arm whose answer depends on the operator knowing that a SQL or workflow directory should be a package — an operator who does not know registers nothing, and the framework cannot tell; one more question on every brownfield run; and every registered directory lengthens `PROJECT_PATHS` in each agent file (F10).

**Consequences.** (b) + (c): Phase 2 builds the verb; Phase 4 rewrites Step 4. (a) alone: Phase 2 drops, and detection becomes an instruction no test can pin. (c) alone: Phase 2 drops, and Terraform depends on the operator naming it.

### D3 — Record shape for a manifest-less package

- **(a) `manifest: null`**, written by a new **`--no-manifest`** flag forming a REQUIRED mutually exclusive argparse group with `--manifest` — omitting both still errors, and giving both errors. ⚠ **The group is a departure, flagged as such:** no subparser in `build_parser` uses a mutually exclusive group today — each required argument is a plain `required=True`, `sp.add_argument("--manifest", required=True)` among them. Justification: omitting both flags must still error, and a plain `required=True` on `--manifest` would also reject `--no-manifest` alone. `summary` renders a null manifest as `null` through `init_helper._render_scalar_for_summary`, whose docstring reads *"`None` becomes the literal lowercase string `null` (matching the on-disk yaml form so the summary mirrors the file)."* — the function `_render_summary` already applies to its workspace fields, followed for consistency. `docs/structure.md`'s `none` (F4) is a different file's token and stays as it is.
- **(b) A new record field**, e.g. `kind` — a schema change; `emit_yaml` writes only `path` and `manifest` today, so the emitter must change or the field is silently lost on the next re-emit (F2).
- **(c) A marker filename**, e.g. `main.tf`, in `manifest` — no schema change, but the field then names a file that is not a manifest, every reader is misled, and a declared SQL or YAML directory has no single file to name.

**RECOMMEND (a).** It follows `index_helper`'s existing `manifest_file: None` convention (F4), needs no new field, the parser already round-trips it (F2), and the Python readers already tolerate it (F5).

**Counter-argument, recorded:** `null` says what a package lacks, not what it is; a consumer that wants "Terraform" must re-derive it from the files — which D4's `language_hint` does, once, in Python.

**Consequences.** Phase 1 builds the flag, the argparse group and `_render_summary`'s `null` through `_render_scalar_for_summary`. `cmd_verify`'s `_scan_for_manifests` is unaffected — it runs only when `packages_detected` is empty (F3). `_PACKAGES_DETECTED_PATH_RE` matches `- path:` lines only, so a `manifest: null` line does not reach it (F5; a code read — Phase 1's Verify re-checks it).

### D4 — `/devforge:configure` composition for a null-manifest package

*(amended after the close, 2026-10-07 — `### Post-close amendments — 2026-10-07` amends (a)'s manifest-less signal, extends (b) to a project whose registered packages are all manifest-less, and corrects the "Phase 3 override" claims of (a) and (c); that subsection is the ruling, and the text below stays as drafted)*

**(a) The per-package record. RECOMMEND:**
- `read-manifests` gains a Python-derived **`language_hint`** — ⚠ a NEW output field, following the existing `*_hint` pattern (F10). It is computed from the package's `index.json` `files[]` through a closed extension map — `.tf` → `HCL`, `.sql` → `SQL`, `.yaml` / `.yml` → `YAML` — **for packages whose `manifest_file` is null only**. It is `null` on every other entry and when no mapped extension occurs; when several occur it is the language with the most files, ties broken by the map's order. The key is present on every entry, so the output shape stays uniform.
- The configure spec gains a rule for a package whose `manifest` is null: `language` = `language_hint`, and that value joins `LANGUAGES`; `framework` and `build_tool` are null, which the existing verbatim rules already produce (F10); `build_command`, `type_check_command` and `lint_command` are `N/A`; `test_command` is `null` — **no invented command**, mirroring the existing `test_command` rule.
- **Consequence:** a touched `*.tf` file then matches its own package by F12's longest-prefix rule and runs nothing, instead of index 0's unrelated commands.
- **Rejected:** `terraform fmt -check` / `terraform validate` defaults. `terraform validate` needs a prior `terraform init` with provider downloads (a Terraform-domain claim, NOT a tree fact), and commands run with cwd = source root (`_cmds_verify.py`'s docstring: *"run with cwd = source_root"* — plan 116's subject). An operator can set commands by hand as a Phase 3 override at `/devforge:configure`'s bulk confirmation.

**(b) The four flat command arrays** — index 0 is load-bearing (F16).
- **(i)** A null-manifest package gets NO entry in `BUILD_COMMANDS` / `TYPE_CHECK_COMMANDS` / `LINT_COMMANDS` / `TEST_COMMANDS`; its `N/A`s live in its `PACKAGE_STACKS` record only.
- **(ii)** Its entries are included, but never at index 0.
- **(iii)** Its entries are included in `MANIFESTS_JSON` order — today's rule, applied unchanged.

**RECOMMEND (i).** Every helper that picks one entry picks index 0 (F16), so dropping these entries changes nothing a helper reads except index 0's safety, and it keeps `N/A` noise out of the rendered `{{BUILD_COMMAND}}` lines. Under (iii) a null-manifest package whose path sorts first, in a project with no `.` record, takes index 0 (F16).

**(c) `language` when `language_hint` is null too** — e.g. a declared directory holding only shell scripts. `set-package-stacks` refuses a null `language` (F10). **RECOMMEND the literal `Unknown`** — ⚠ a NEW token no other rule produces, flagged as such — which the user corrects as a Phase 3 override. Alternative, not recommended: leave such a package out of `PACKAGE_STACKS`, which puts its files back on F12's index-0 fallback.

**Counter-argument to D4 as a whole, recorded and NOT answered away:** an infra edit is now verified by nothing — and silently, since `N/A` is skipped silently (F12). Today it is verified by unrelated commands, which is no better, but which at least runs something. **Against (b) (i):** it breaks the spec's *"aligned per-package"* wording for those arrays and the `PACKAGE_STACKS` bullet's *"same per-package values used by the flat string-arrays above"*, which Phase 5 must reword; (ii) keeps the alignment at the price of a placement rule an LLM composer must remember.

**Consequences.** Phase 3 adds `language_hint`; Phase 5 writes (a)'s rule, (b)'s ruling and (c)'s ruling into the configure spec.

### D5 — Gate 2 design (only if D1 rules (a))

**RECOMMEND all six parts:**
- **(i) ONE owner for the concern-root path, introduced first as a behavior-preserving refactor.** A single module — working name `_concern_root.py` (⚠ a working name) — owns ONLY the concern-root PATH computation: the package's root directory (`<pkg>`, consumed by (v)), the directory a package's concerns are enumerated under (`<pkg>/src` today), a concern's directory (`<pkg>/src/<concern>` today; the fallback root `<pkg>/` under (ii)) and its package-relative prefix (`src/<concern>/` today); every F7 site calls it. **Each site keeps its own skip predicate unchanged** — the two concern enumerations, `_preflight._enumerate_concerns` and `_package_input._enumerate_concerns`, skip different names (F20), and unifying them is a `## Non-goals` item (Trap 15) — so Phase 6 is behavior-preserving. Those predicates filter the children of `<pkg>/src/` only and are never applied to the fallback concern's own name: under OQ-2's recommendation a package at `infra/build` names its concern `build`, which preflight's predicate would skip. **Precedent — the codebase's single-owner pattern:** `src/devforge/lib/_shared/memory.py`, the single owner of the `.devforge/memory.md` literal (the root `CLAUDE.md` router).
- **(ii) The fallback.** A non-`.` package with no `<pkg>/src/` directory becomes ONE concern rooted at `<pkg>/`, named per OQ-2. The existing split path — `_diff_concern`'s docstring: *"when … the concern's total span exceeds the threshold AND it has ≥ 2 immediate child dirs"* — subdivides a large one, and its loose files flow through the existing `loose_files`.
- **(iii) `.` keeps the `src/` requirement.** In a standalone install the forge's own artifacts sit at the project root — `docs/`, `specs/` and `constitution.md` (`src/CLAUDE.md` `## Artifact Storage`), `bugs/` and `tickets/` (its command list) and `CLAUDE.md` itself — and a fallback for `.` would document them as concerns. In a monorepo `.` is skipped already (F6).
- **(iv) The fallback walk skips dot-prefixed directories** (F17) — `.terraform/` among them — in both the file walk and the split's immediate-dir enumeration, **when the root is the fallback only**; a `src/` concern keeps today's dot-directory behavior.
- **(v) The trivial-leaf filter tests only the path components BELOW the package root, in both layouts** (F21). `_walk_concern_subfolder` and `_enumerate_immediate_dirs` stop passing the package's own path components to `_path_contains_trivial_dir`, which matches the three prefix sites, whose `index.json` paths are package-relative already. ⚠ **A signature change, stated:** `_enumerate_immediate_dirs(subfolder_abs, project_root)` takes no package argument, and `_walk_concern_subfolder` computes `rel` relative to `project_root`. Both take the package root from the owner module (`_concern_root.py`, working name, D5 (i)): `_walk_concern_subfolder` derives it from its `pkg` argument, and `_enumerate_immediate_dirs` gains a package-root parameter that its two callers, `_preflight._diff_concern` and `_concern_input.cmd_concern_input`, fill from the owner. Phase 6's owner exposes the package root, so Phase 7 does not invent it. ⚠ **A behavior change, flagged as such:** it also fixes the pre-existing `src/`-layout case F21 records — a package at `packages/assets` gets its concerns' files back. **Counter-argument, recorded:** it widens Phase 7 into the `src/` layout's existing behavior, beyond the fallback this plan is about.
- **(vi) The `src-root` tier is empty under the fallback.** `_package_input.py` `_collect_src_root_files` — docstring *"Walk `<project_root>/<pkg>/src/` for direct files (non-dir)."* — feeds `src_root_files` and the `src-root` part of the package stamp (`_compute_source_stamp`: `parts.append(f"src-root\t{path}\t{h}")`). For a fallback package it returns no records and no hashes: the loose files at `<pkg>/` already belong to the single concern and reach the package stamp through that concern's `source_stamp`, so a `src-root` tier would hash them a second time. Today's `if not src_dir.is_dir():` branch already yields that outcome; the owner never repoints this function at the fallback root. The `_PACKAGE_ROOT_FILES` names keep their `root` tier — the double reading the counter-argument below records.

**Alternatives, not recommended:** (a') the package root's subdirectories as concerns — a flat root module's `*.tf` files at `<pkg>/` would belong to no concern; (b') the fallback for `manifest: null` packages only — a narrower blast radius, but arbitrary: a flat-layout package with a manifest has the same gap (F6).

**Counter-argument, recorded and NOT answered away:** it changes `/devforge:generate-docs` output on existing installs that have flat-layout non-`.` packages — their next run writes concern and package docs where none existed. The stamp gate leaves existing `src/` docs untouched (`_classify_status` maps an equal stamp to `unchanged`), but the new docs are unasked-for on those installs. And a concern rooted at `<pkg>/` walks the package-root files (README, CHANGELOG, manifests) that `package-input`'s `_collect_package_root_files` also reads, so those files are seen at both tiers.

**Consequences.** Phase 6 builds (i); Phase 7 builds (ii)–(vi) and classifies the `src/` layout statements in `src/devforge/lib/_generate_docs/`'s docstrings, comments and user-facing messages; Phase 8 sweeps the layout statements in the markdown files it lists.

### OQ-1 — Were SQL procedure trees or workflow-definition YAML packages present in the observed project?

**A maintainer answer, not a design question.** It changes only the evidence class of D2's free-text arm: if absent, that arm meets a predicted need, and the close record says so. It changes no phase.

### OQ-2 — The concern name for D5's single-concern fallback

**RECOMMEND the package directory's basename** — e.g. `tf` for a package at `infra/tf` — because the name is shown to readers: in the package overview's `Concerns` list and in the concern doc's `concern` frontmatter, where a fixed token such as `root` carries no meaning. ⚠ **Neither candidate is collision-free:** a concern's doc lives at `docs/<pkg>/<concern>/index.md` (`_package_input._read_concern_seed`) and a package's overview at `docs/<P>/overview.md` (`src/commands/generate-docs/main.md` Phase 3), so a registered package at `<pkg>/<name>` shares the directory `docs/<pkg>/<name>/` with a concern `<name>` of `<pkg>` — a property `src/` concerns already have.

### OQ-3 — Where the out-of-scope observations are recorded

- **F15** (`.` never matches) and **F18** (the hand-back arms versus `### Never` item 7): **RECOMMEND a `FINDINGS.md` entry each** — both have no owner — written in Phase 9 through the instruction-author → instruction-reviewer flow.
- **F20** (the two concern enumerations' skip rules) and **F21** (the trivial-leaf filter sees the package's own path components): **RECOMMEND one ownership rule for every D1 and D5 outcome — the F20 / F21 ownership rule, stated here once and cited by name elsewhere: Phase 9 writes one `FINDINGS.md` entry recording each of F20 and F21 that no ratified phase of this plan fixes and that the D1 (c) stub does not carry**, written through the instruction-author → instruction-reviewer flow. Both findings are pre-existing and plan 101 is closed (F9), so a finding this plan neither fixes nor hands to the D1 (c) stub has no owner once this plan closes. Its cases, stated so no builder computes them: D1 (a) with D5 (v) ratified → the entry records F20 only (Phase 7 fixes F21; F20 is a `## Non-goals` item); D1 (a) with D5 (v) declined → the entry records F20 and F21; D1 (b) → the entry records F20 and F21 (Phases 6–8 drop); D1 (c) → no entry (the new stub carries both). Under D1 (a) with D5 (v) amended, the Phase 0 close record states whether the amended (v) fixes F21, and the matching D1 (a) case above applies.
- **F19** (the stale 500-file cap, at its six sites): **RECOMMEND fixing it in place, only in phases that run under every D1 outcome** — Phase 1 for the two code docstrings (`index_helper.py`'s and `_concern_input.py`'s, through Phase 1's python-engineer → python-reviewer route), Phase 4 for `init-forge/main.md` Step 6 and `docs/v2/ARCHITECTURE.md`'s three stale-cap hits. Phase 4 already edits Step 6's per-package bullet, and leaving a known-false clause in an edited sentence breaks the repo's cross-check rule; `docs/v2/ARCHITECTURE.md`'s `_concern_input.py` row, whose layout wording Phase 8 rewrites under D1 (a) only, does not wait on D1 for its cap clause. Declined, F19 is still corrected in each sentence a phase edits for another reason — Step 6's per-package bullet (Phase 4) and, under D1 (a), the `_concern_input.py` row (Phase 8) — so whatever records a declined F19 names only the sites still stale after those phases.
**Counter, recorded:** F19's fix is scope creep in a plan about manifest-less packages; the alternative is one more `FINDINGS.md` entry.

### OQ-4 — Does `add-package --no-manifest` check that the directory exists?

`_validate_path` checks no existence (F2). With a manifest, the walk saw the file, so the directory existed; a path typed at D2's free-text arm has no such guarantee, and `build-index` turns a missing directory into a skipped record and a stderr line, not a failure (F4). **RECOMMEND yes:** under `--no-manifest`, `add-package` exits 2 when `<project_root>/<path>` is not a directory, resolving `project_root` as `cmd_verify` does (`_resolve_project_root`). **Counter, recorded:** an asymmetry between the two flags, and a dependency on `set-project-root` having run — which Step 1 always does before Step 4.

### OQ-5 — Does D5's fallback concern exclude a nested registered package?

No concern walk excludes nested packages today: `_walk_concern_subfolder` filters only trivial-leaf components (F17). Under the fallback rooted at `<pkg>/`, a registered package below `<pkg>/` (D2's edge) would be documented under both. **RECOMMEND excluding it, in the fallback walk only;** the registered paths are the `index.json` package keys preflight already reads. ⚠ **The exclusion applies preflight's prefix:** those keys are relative to `index.json`'s own `project_root`, and `_preflight._enumerate_concerns` bridges them with a prefix — its comment: *"Bridge index.json's package keys (relative to its project_root) to paths relative to F.0's caller-supplied project_root."* An exclusion that compares unprefixed keys against the walk's paths fails in wrapper installs. **Counter, recorded:** asymmetric with `src/` concerns, which do not exclude.

### Phase 0 close record

**CLOSED 2026-10-07.** D1 and OQ-1 were closed by explicit pick: **D1 (a), both gates, as recommended; OQ-1, which carried no recommendation, answered — only Terraform was present in the observed project.** D2, D3, D4, D5, OQ-2, OQ-3, OQ-4 and OQ-5 were **ratified as recommended** by one blanket pick. Nothing was amended, nothing was declined, no item is left open, and **build phases may start, in this plan's build order — NOTHING is built yet** (*What this record does NOT close*, below).

Every statement in this record is dated 2026-10-07 unless it names another date.

**How it closed — 2026-10-07.**

- **The maintainer's opening message**, by English paraphrase: *"Implement plan 112."*
- **ONE `AskUserQuestion` call carrying three questions**, recorded by English paraphrase:
  - **D1** — options (a) both gates, **the option the tool labelled `(Recommended)`**; (b) Gate 1 only; (c) Gate 1 plus a new stub. **Picked: (a).**
  - **OQ-1** — asked, by English paraphrase, whether SQL procedure trees or workflow-definition YAML packages were present in the observed project, not only Terraform — options: yes, they were; no, only Terraform; don't remember. No option was labelled `(Recommended)`: OQ-1 is a maintainer answer. **Picked: no, only Terraform.**
  - **Every other item** — asked, by English paraphrase, whether to ratify the rest (D2–D5, OQ-2–OQ-5) as recommended — options: yes, all as recommended, **labelled `(Recommended)`**; walk item by item. **Picked: yes, all as recommended.**
- **No per-item deliberation was supplied for D2, D3, D4, D5, OQ-2, OQ-3, OQ-4 or OQ-5, and this record says so.** The blanket pick's "as recommended" means each item's own RECOMMEND under `## Phase 0 — ratification` — its working names and its ⚠-flagged departures included — and that is what this record ratifies.
- **All three are PICKS, not delegations:** the maintainer chose named outcomes rather than handing the decisions back.
- **Every counter-argument stays, unshortened.** Nothing under `## Phase 0 — ratification` is deleted, shortened or answered away by this close. Its lead keeps its opening sentence, *"Nothing below is ratified."*, with a dated pointer beside it naming this close, and each item's text stays as drafted, the options not taken included. **This record is the ruling.**
- **Re-verified before the close.** The `## When resuming work` step 4 greps were re-run: every F1–F21 quote was found in the tree; F7's three-pattern sweep returned 14 lines and `git grep -n 'src/' -- src/devforge/lib/_generate_docs/` returned 35, both matching the drafting baselines. HEAD had not moved since the drafting reads: the drafting baseline was `44d9e1c`, and the only commit after it was this plan's own draft, `d2cbe5b` (*"Phase 0 OPEN"*). ⚠ **F12, F14 and F15 — runs, not reads — were NOT re-run.**

**Outcomes — 2026-10-07.**

| Item | Outcome | What it settles |
|---|---|---|
| D1 | Ratified as recommended, by explicit pick — **(a), both gates** | Phases 1–5 fix Gate 1 and Phases 6–8 fix Gate 2; every phase 1–9 runs. **Phase 10's docs anchor (c) is a pass criterion**, not record-only. D5, OQ-2 and OQ-5 are live, not moot. This plan takes on what plan 101's OQ-5 declined; plan 101 is not edited (F9). Under OQ-3's F20 / F21 ownership rule, with D5 (v) ratified, Phase 9's entry records **F20 only** (OQ-3's row). |
| D2 | Ratified as recommended — **(b) + (c)**; verb **`detect-manifest-less`**; hand-back **as recommended, with its flagged departure** | **Mechanism:** the mechanical `init_helper` verb, with D2's detection rules unchanged, plus Step 4's free-text declaration for kinds with no reliable signal. **The working name `detect-manifest-less` is adopted** — the only name proposed, ratified by the blanket pick; Phases 2 and 4 use it, and no later phase renames it. The candidate question's options are exactly `Register all` (Recommended), `Let me choose which` and `Register none`. **Hand-back:** at the candidate question, every detected candidate is registered and named in Step 5's delegated-values lines; at the free-text declaration, the question is asked once more and a second hand-back registers nothing from it; Step 5's delegated-values sentence gains Step 4. ⚠ **The flagged departure stands:** at the `Let me choose which` prompt, the question is asked once more, and a second hand-back registers every detected candidate, named the same way. |
| D3 | Ratified as recommended — **(a), `manifest: null` via `--no-manifest`** | `--no-manifest` and `--manifest` form a REQUIRED mutually exclusive argparse group — ⚠ **the flagged departure stands**; neither flag, or both, errors. `summary` renders a null manifest as `null` through `_render_scalar_for_summary`; `docs/structure.md`'s `none` stays (F4). No new record field. |
| D4 | Ratified as recommended — **(a)** `language_hint`; **(b) (i)**; **(c)** the literal `Unknown` | **(a):** `read-manifests` gains `language_hint` on every entry — the closed map `.tf` → `HCL`, `.sql` → `SQL`, `.yaml` / `.yml` → `YAML`; computed for null-manifest packages only; the majority language, ties by the map's order; `null` otherwise. A null-manifest package's `language` is its `language_hint`, joining `LANGUAGES`; `framework` and `build_tool` are null; `build_command`, `type_check_command` and `lint_command` are `N/A`; `test_command` is `null`. **(b) (i):** a null-manifest package gets NO entry in `BUILD_COMMANDS` / `TYPE_CHECK_COMMANDS` / `LINT_COMMANDS` / `TEST_COMMANDS`. **(c):** when `language_hint` is null too, `language` is the literal `Unknown` — ⚠ **the flagged new token stands** — which the user corrects as a `/devforge:configure` Phase 3 override. |
| D5 | Ratified as recommended — **all six parts, (i)–(vi)**; owner module **`_concern_root.py`** | **(i)** one owner of the concern-root path, introduced as a behavior-preserving refactor, each site keeping its own skip predicate (F20); **the working name `_concern_root.py` is adopted**, under `src/devforge/lib/_generate_docs/`. **(ii)** a non-`.` package with no `<pkg>/src/` becomes one concern rooted at `<pkg>/`, named per OQ-2. **(iii)** `.` keeps the `src/` requirement. **(iv)** the fallback walk skips dot-prefixed directories, under the fallback root only. **(v)** the trivial-leaf filter tests only the path components below the package root, in both layouts — ⚠ **a stated behavior change** for `src/`-layout packages whose path holds a `_TRIVIAL_LEAF_DIRS` name; it fixes F21. **(vi)** the `src-root` tier is empty under the fallback. |
| OQ-1 | **Answered by the maintainer, by explicit pick: only Terraform was present in the observed project** — OQ-1 carried no recommendation to ratify, amend or decline | Per OQ-1's own text, **D2's free-text arm meets a PREDICTED need, not an observed one.** It changes no phase. ⚠ **The answer is the maintainer's recollection, recorded by paraphrase; no artifact of the observed project is in this repo, so it changes NO evidence class.** |
| OQ-2 | Ratified as recommended — **the package directory's basename** | The fallback concern of a package at `infra/tf` is named `tf`. The `docs/<pkg>/<name>/` collision OQ-2 records stays as it is, a property `src/` concerns already have. |
| OQ-3 | Ratified as recommended | **F15** and **F18** — one `FINDINGS.md` entry each, written in Phase 9 through the instruction-author → instruction-reviewer flow. **F19** — fixed in place: Phase 1 for the two code docstrings (`index_helper.py`'s and `_concern_input.py`'s), Phase 4 for the four docs sites (`src/commands/init-forge/main.md` Step 6 and `docs/v2/ARCHITECTURE.md`'s three stale-cap hits); **never Phase 8.** **The F20 / F21 ownership rule's case — D1 (a) with D5 (v) ratified: Phase 9's entry records F20 ONLY** — Phase 7 fixes F21, and F20 is a `## Non-goals` item. |
| OQ-4 | Ratified as recommended — **yes** | Under `--no-manifest`, `add-package` exits 2 when `<project_root>/<path>` is not a directory, resolving `project_root` as `cmd_verify` does (`_resolve_project_root`). Under `--manifest`, behavior is unchanged. |
| OQ-5 | Ratified as recommended — **exclude** | A registered package nested below a fallback package's root is excluded from the fallback concern, in the fallback walk only, applying preflight's prefix to the `index.json` package keys. `src/` concerns keep today's non-exclusion. |

**What the outcomes put in scope — 2026-10-07.** Derived from each phase's Deliverables under the rulings above; the Deliverables stay authoritative.

- **Phase 1 — D3 (a), OQ-4 yes, OQ-3's F19 docstring part.** `init_helper.py` `build_parser` (the required mutually exclusive group), `cmd_add_package` (`manifest: None` under `--no-manifest`, and the existence check) and `_render_summary` (the manifest column through `_render_scalar_for_summary`); the module-docstring corrections in `src/devforge/lib/index_helper.py` and `src/devforge/lib/_generate_docs/_concern_input.py`; tests in `tests/lib/test_init_helper.py`, plus the chain tests in `tests/lib/test_index_helper.py` and `tests/lib/test_configure_helper.py`.
- **Phase 2 — D2 (b).** The verb `detect-manifest-less` in `init_helper.py`, with its subparser, and its planted-tree tests in `tests/lib/test_init_helper.py`.
- **Phase 3 — D4 (a).** `_configure/_cmds_read.py` `cmd_read_manifests`: `language_hint` on every entry, its extension map one closed constant; tests in `tests/lib/test_configure_helper.py`.
- **Phase 4 — D2 (b) + (c) and its hand-back form, D3 (a), OQ-3's F19 docs part.** `src/commands/init-forge/main.md` — `## Step 4: Discover packages` (the `detect-manifest-less` call after the manifest walk, the three-option candidate question, the free-text declaration, the `add-package --no-manifest` call, and the hand-back arms, the flagged `Let me choose which` arm included), `## Outputs of this phase`, Step 5's delegated-values sentence, and Step 6's per-package bullet (its manifest clause and its cap clause); `docs/v2/ARCHITECTURE.md`'s three stale-cap hits. In Phase 4's Verify, `<the ratified verb name>` is `detect-manifest-less`; the declined-F19 bullet does not apply.
- **Phase 5 — D4 (a), (b) (i), (c).** `src/commands/configure/main.md` — the `read-manifests` shape sentence names `language_hint`; the `LANGUAGES` and `PACKAGE_STACKS` `language` rules, D4 (c)'s `Unknown` included; the null-manifest commands rule; the five `**Per-package**` bullets, reworded so a null-manifest package has no flat-array entry.
- **Phase 6 — D5 (i).** The owner module `_concern_root.py` under `src/devforge/lib/_generate_docs/`, with its tests; every F7 site rewritten to call it for the concern-root path only; the three layout-embedding messages; the package-root accessor Phase 7 consumes. No output changes.
- **Phase 7 — D5 (ii)–(vi), OQ-2, OQ-5.** The fallback root; the dot-directory skip under it; `_walk_concern_subfolder` and `_enumerate_immediate_dirs` testing only components below the package root, `_enumerate_immediate_dirs` gaining the package-root parameter that `_preflight._diff_concern` and `_concern_input.cmd_concern_input` fill; `_collect_src_root_files` yielding nothing for a fallback package; the basename concern name; the nested-package exclusion through preflight's prefix; tests; and the `src/` statements under `src/devforge/lib/_generate_docs/`, classified per Phase 7's Deliverables.
- **Phase 8 — D1 (a), D5.** The layout statements in `src/commands/generate-docs/main.md`, `src/CLAUDE.md`, `src/agents/tech-writer.md`, `src/devforge/storage-rules.md` and `docs/v2/ARCHITECTURE.md` (the `_concern_input.py` row's layout wording, and a row for `_concern_root.py`). That row's cap clause is Phase 4's under OQ-3, so Phase 8's declined-F19 branch does not apply.
- **Phase 9 — every ruling.** `CHANGELOG.md`, `DEVELOPMENT-STATUS.md`, `PLAN-STATUS-ARCHIVE.md`; **three `FINDINGS.md` entries — F15, F18 and F20, one each** — F20's per OQ-3's F20 / F21 ownership rule, with no F21 entry; the root `CLAUDE.md` router grep for `--no-manifest`, `language_hint`, `detect-manifest-less` and `_concern_root.py`. No D1 (c) stub is written. Per `## Overlap with other plans` — not Phase 9's Deliverables — its ledger entries also say plan 101's residual 12 is addressed here.

**What this record does NOT close — 2026-10-07.**

- **Nothing is built.** Phases 1–9 have not started; they run in this plan's build order, 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 (`## Phases`). **Queue position, read 2026-10-07:** every root plan file numbered 101 to 111 — no 103 file exists — reads DONE (build), CLOSED or DECLINED on its `**Status**:` line (110 DECLINED; 109 and 111 DONE (build)). The maintainer's directive was to implement this plan, so the build starts now, at Phase 1. ⚠ **This record makes no claim about any root plan numbered below 101.**
- **Phase 10 is user-driven and DEFERRED** — run by the maintainer, on a consumer install the maintainer picks, never the frozen benchmark install. Until it runs, "built and build-verified" is the ceiling of every claim this plan makes.
- **`### Honest bounds`' residuals stand, unchanged by any ruling:** a root holding `*.tf` files still gets no docs (D5 (iii)); D4 leaves infra edits unverified, silently; D5 changes output for existing installs — flat-layout non-`.` packages gain docs where none existed, and under D5 (v) `src/`-layout packages whose path holds a `_TRIVIAL_LEAF_DIRS` name gain the files the walk drops today (F21).
- ⚠ **Ratification changes no evidence class: ONE consumer observation, with NO artifact of it in this repo and NOTHING measured; plus one PLANTED codebase-graph probe (F14) and direct helper calls (F12, F15).** The run observed the symptom, not Gate 2 (Trap 11), and OQ-1's answer is the maintainer's recollection, not an artifact.

#### Verify

- The record names **each** of D1, D2, D3, D4, D5, OQ-1, OQ-2, OQ-3, OQ-4 and OQ-5 with an explicit outcome — ratified, amended or declined — **checked by name, never against a range.**
- **D1 names (a), (b) or (c).** Under (b) or (c), D5, OQ-2 and OQ-5 are recorded *moot*, and Phases 6–8 are recorded as not running. Under OQ-3's F20 / F21 ownership rule, the record states which of F20 and F21 Phase 9's `FINDINGS.md` entry records, or that no entry is written — the rule's case for the ratified D1 outcome and, under D1 (a), the D5 (v) outcome.
- **OQ-3 names an outcome for each of F15, F18 and F19, and for its F20 / F21 ownership rule.** Under its F19 recommendation, F19's sites are routed to Phase 1 (the two code docstrings) and Phase 4 (the four docs sites), never to Phase 8, which runs only under D1 (a).
- **D2 names its mechanism and its hand-back form; D4 names a ruling for each of (a), (b) and (c); under D1 (a), D5 names a ruling for each of (i), (ii), (iii), (iv), (v) and (vi).**
- **Every counter-argument above is still present, unshortened.**
- **The record repeats the evidence class unchanged**: ONE consumer observation with no artifact here and nothing measured; one planted probe; direct helper calls. **Ratification changes no evidence class.**

### Post-close amendments — 2026-10-07

Every statement in this subsection is dated 2026-10-07 unless it names another date.

**How it was decided — 2026-10-07.** During Phase 5's authoring, the Phase 5 author reported three problems in the ratified D4, and the orchestrator confirmed each against the code by reading it — nothing was run on a consumer. The maintainer was then asked through ONE `AskUserQuestion` call carrying three questions, recorded here by English paraphrase; each question listed its recommended option first, labelled `(Recommended)`. **The maintainer picked the recommended option on all three — explicit picks, not a delegation.**

**Rulings — 2026-10-07.**

- **A — D4 (a) AMENDED: the manifest-less signal.**
  - **Problem.** `index_helper` re-detects a package's manifest from `_MANIFEST_REGISTRY` only and ignores the `init.yaml` `manifest` value (F4). Step 4 also registers packages by `pubspec.yaml`, `*.gemspec` and `mix.exs` (F1), none of which `_MANIFEST_REGISTRY` carries — F3's disagreeing lists — so such a package indexes as `manifest_file: null`. D4 (a) as ratified computes `language_hint` *"for packages whose `manifest_file` is null only"*, so a Flutter package holding `pubspec.yaml` and `analysis_options.yaml`, whose `.dart` files the closed map does not carry, would get a `language_hint` of `YAML`, `N/A` build, type-check and lint commands, and no flat-array entry.
  - **Ruling.** A package is manifest-less exactly when its `init.yaml` record has `manifest: null` — the value only `add-package --no-manifest` writes (D3, Phase 1).
  - **Consequence.** Phase 3's `read-manifests` reads `init.yaml` and emits a non-null `language_hint` only for such a package, and `null` on every entry when `init.yaml` is unreadable. Once that change lands, two F5 sentences stop holding — *"No Python reader branches on the `init.yaml` `manifest` value"* and *"`configure_helper read-manifests` reads `index.json` records, not `init.yaml`"* — and F10's *"spreads each `index.json` record into the package dict it reads"* no longer names everything `cmd_read_manifests` reads. F5 and F10 stay as written: they are dated reads. Phase 5's rules key on `INIT_JSON.packages_detected[].manifest` — the `init.yaml` value. Phase 3 was committed before this amendment (`0699d40`); a follow-up commit brings it in line, and `git log --oneline --grep 'plan-112'` lists that commit once it is made.
  - **Not picked.** Keeping D4 (a) as ratified; extending `_MANIFEST_REGISTRY` — plan 118's territory (Trap 2).
- **B — D4 (b) EXTENDED: packages registered, none manifest-bearing.**
  - **Problem.** Under D4 (b) (i), a project whose registered packages are all manifest-less — a repo of Terraform root modules only, for instance — composes four EMPTY flat arrays. The `set-*-commands` setters refuse an empty array (*"value cannot be empty"*, `_configure/_validators.py`), and `configure_helper verify` flags one (*"required field {0} is empty"*, `_configure/_cmds_verify.py`).
  - **Ruling.** When at least one package is registered and none is manifest-bearing, each of `BUILD_COMMANDS`, `TYPE_CHECK_COMMANDS`, `LINT_COMMANDS` and `TEST_COMMANDS` is the single entry `N/A`. Every index-0 reader (F16) skips `N/A`: `cmd_verify_touched` silently (F12), `_get_test_command` by returning `None`, and the configure probe by skipping the command. Trap 9's effect still holds — a file inside no package then runs nothing — but such a project has no manifest-bearing command for `N/A` to displace.
  - **Consequence.** Phase 5 writes this rule beside D4 (b) (i)'s.
  - **Not picked.** Making the setters and `verify` accept an empty array — a Python change; leaving it as ratified — a project of manifest-less packages only would then fail at `/devforge:configure`.
  - ⚠ **Not addressed, recorded honestly:** a project with ZERO registered packages already composed four empty arrays before this plan — the per-package alignment rules (F10) give it no entry — and this amendment leaves that pre-existing case as it is.
- **C — D4 (a)'s and (c)'s "Phase 3 override" claim was FALSE; AMENDED.**
  - **Problem.** D4 (a) says *"An operator can set commands by hand as a Phase 3 override at `/devforge:configure`'s bulk confirmation."*, and D4 (c) says the user corrects `Unknown` *"as a Phase 3 override"*. But before Phase 5 — as of `ef98d8c` — `src/commands/configure/main.md`'s `## Phase 3 — Bulk-confirmation prompt` echoed `package_stacks` as one line, *"package_stacks: <count> packages — <list path entries>"*, and its `### Parsing the user reply` read overrides only as lines it could *"parse line-by-line as `<field>: <value>`"* — it had no per-record override for `package_stacks`.
  - **Ruling.** Phase 5 adds a per-record override form to that Phase 3 — `package_stacks <path> <key>: <value>` — and the echo lists each record as `<path> (<language>)`.
  - **Consequence.** Phase 5's deliverables widen to that section's echo template, its `### Parsing the user reply` and its `### Setter mapping`. Two other sections of the same file parse a reply of their own — `### Phase 5.2 — Prune agents`' `#### Parsing the user reply` and `## Phase 6 — Exclude framework folders from project linters`' `### Parsing the user reply` — and this amendment reaches neither.
  - **Not picked.** Dropping the promise; recording the gap in `FINDINGS.md`.

**What stands — 2026-10-07.**

- **What the amendments do NOT change.** D4 (a)'s closed extension map, its majority and tie rules, and its composition rule for a manifest-less package; D4 (b) (i) wherever at least one registered package is manifest-bearing; D4 (c)'s `Unknown`. No other item's outcome moves.
- **D4's drafting text and the close record stay as written.** Dated pointers under `### D4` and under Phase 3's and Phase 5's `#### Deliverables` name this subsection, and the close record's *"Nothing is built."* describes the state at the close — `**Status**:` says where the build stands. **This subsection is the ruling for these three points: where the close record — its D4 row, or its Phase 3 and Phase 5 bullets under *What the outcomes put in scope* — conflicts with it or falls short of it, this subsection wins.**
- ⚠ **Evidence class unchanged.** The amendments rest on code reads of this tree; nothing was run. The evidence class stays ONE consumer observation, with NO artifact of it in this repo and NOTHING measured; plus one PLANTED codebase-graph probe (F14) and direct helper calls (F12, F15).

**Orchestration note — 2026-10-07 (not a maintainer ruling).**

- **The build departed from `## Phases`' order 1 → 2 → … → 9.** Phase 6 (`6a23837`) was committed before Phase 4 (`1d8e6fb`) and before Phase 5, because Phase 6 depends on neither — `## Phases` names no prerequisite for it — and Phase 7 needs its owner. Phase 7 (`ef98d8c`) also landed before Phase 5, after its prerequisites, Phases 1 and 6, were committed. Every prerequisite `## Phases`' dependency statements name — Phases 1 and 2 for Phase 4, Phase 3 for Phase 5, Phases 1 and 6 for Phase 7 — was committed before Phase 4, the first dependent phase to land. **The build log, `git log --oneline --grep 'plan-112'`, is the authoritative order;** `## Phases`' build-order sentence stays as drafted.
- **A Phase 7 follow-up implements D5 (iii) in wrapper installs — a fix, not an amendment.** D5 (iii) keeps the project root (`index.json` key `.`) on the `src/` requirement. Phase 7's code as committed (`ef98d8c`) recognized the root by comparing the bridged package path to `"."`, which a wrapper install's bridged root, `<inner>`, never equals — so a wrapper's inner root with no `src/` fell back to a single concern, contrary to ratified D5 (iii). The fix makes the project root never fall back in wrapper installs too, implementing D5 (iii) as written. It landed as a separate follow-up commit, `7330117`.

---

## Phases

Phase 0 is the section above; **nothing below starts before its close record exists.**

**Build order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9; Phase 10 is user-driven and deferred.** Phases 1–5 are Gate 1 and ship whatever D1 rules; Phase 4 cites Phases 1 and 2's verb and flag, and Phase 5 cites Phase 3's field. Phases 6–8 run only under D1 (a); Phase 7 needs Phase 6's owner and Phase 1's flag (its fixtures are built through it). Phase 9 runs after every phase that runs.

**Routes.** Python phases: python-engineer → python-reviewer, every Python function with a test written AND run in the same turn. Instruction phases: instruction-author → instruction-reviewer, looping until the review is clean. **Every phase commits by explicit path — never `git add -A`; another session may share the checkout.**

### Phase 1 — `add-package --no-manifest` (D3, OQ-4, OQ-3's F19 docstring part)

#### Deliverables

- `init_helper.py` `build_parser`: `--manifest` and a new `--no-manifest` in a REQUIRED mutually exclusive group — D3's flagged departure.
- `cmd_add_package`: under `--no-manifest`, appends `{"path": path, "manifest": None}`; under OQ-4's ruling, the existence check.
- `_render_summary`: renders the manifest column through `_render_scalar_for_summary`, so a `None` manifest prints `null` and a string manifest prints verbatim (D3).
- Tests in `tests/lib/test_init_helper.py`, plus the chain tests below in `tests/lib/test_index_helper.py` and `tests/lib/test_configure_helper.py`.
- Under OQ-3's F19 recommendation, two docstring-only edits with no behavior change (F19): `src/devforge/lib/index_helper.py`'s module-docstring line *"data: file listings (capped at 500), manifest scripts + dependencies."* and `src/devforge/lib/_generate_docs/_concern_input.py`'s module-docstring *"at 500 entries per package (`files_truncated: true` flag)."*, each corrected against `index_helper._MAX_FILES_PER_PACKAGE` as read at build time; grep `500` in both files and classify every hit in the commit body without quoting any project name (Trap 12). Known hits that stay unedited: those in the comment block directly above `index_helper._MAX_FILES_PER_PACKAGE`, which opens *"# Maximum files listed per package."* — a dated record of the bump from 500 (*"Bumped 500 → 10000"*), classified still true. The block names a project, so the commit body cites it by that opening line and quotes no name from it.
- Under OQ-3's F19 recommendation, `_concern_input.py`'s cap sentence opens the module-docstring paragraph *"Why filesystem and not index.json:"*. Each sentence of that paragraph is re-read against `index_helper._MAX_FILES_PER_PACKAGE`, `index_helper._list_package_files` and `_concern_input._walk_concern_subfolder` as read at build time, and its classification — edited / still true — is recorded in the commit body. The paragraph's rationale stays stated after the edit: the concern walk reads the filesystem because `index.json`'s per-package file list is capped. One sentence of the paragraph cites a historical example by a project name; the commit body names that sentence without quoting the name (Trap 12).

#### Verify

- **Round-trip through the REAL producer chain, never a hand-authored fixture:** `init_helper reset` → `set-project-root` → `add-package --path infra/tf --no-manifest` → `init.yaml` holds the line `    manifest: null` → `parse_yaml` returns `None` for it → `index_helper build-index` → the `index.json` record carries `manifest_file: null`, lists the `*.tf` files and nothing under a planted `.terraform/` → `configure_helper read-manifests` emits `manifest: null`, `build_tool_hint: null`, `framework_hint: null`.
- Argparse: neither flag → exit 2; both flags → exit 2.
- `summary` prints `null` in the manifest column for that record, and an existing `--manifest package.json` record's line is byte-identical to today's.
- `_PACKAGES_DETECTED_PATH_RE` still extracts `infra/tf` from the emitted `init.yaml` (a test, not a read).
- `init_helper verify` on that state raises no `packages_detected` violation.
- Under OQ-4 = yes: a nonexistent path under `--no-manifest` exits 2; under `--manifest`, behavior is unchanged.
- Under OQ-3's F19 recommendation: `git grep -n 500 -- src/devforge/lib/index_helper.py src/devforge/lib/_generate_docs/_concern_input.py` — no docstring line states a 500-file cap, and every hit is classified in the commit body, one at a time, quoting no project name (Trap 12); the hits in the comment block directly above `_MAX_FILES_PER_PACKAGE` are classified still true; `git diff` of those two files changes docstring lines only.
- Under OQ-3's F19 recommendation: the commit body classifies each sentence of `_concern_input.py`'s *"Why filesystem and not index.json:"* paragraph — edited / still true — one at a time, and quotes no project name (Trap 12); the paragraph, re-read after the edit, still states that the concern walk reads the filesystem because `index.json`'s per-package file list is capped.
- The full `tests/lib` suite is green; the python-reviewer loop runs until a review returns no findings.

### Phase 2 — The detection verb (D2)

#### Deliverables

- The verb (working name `detect-manifest-less`, D2) in `init_helper.py`, with its subparser, printing one candidate path per line on stdout (D2) and writing no state.
- Planted-tree tests in `tests/lib/test_init_helper.py`.

#### Verify

- Planted trees, each with its expected candidate list: a flat root module (`infra/main.tf`) → `infra`; an `envs/<x>/` + `modules/<y>/` layout with no `*.tf` above them → each `envs/<x>` and each `modules/<y>`; a root module with a nested `modules/` → the root module only; `.terraform/` holding `*.tf` → not proposed; `node_modules/` and `vendor/` holding `*.tf` → not proposed; a `*.tf` directory inside a registered non-`.` package → excluded; one that IS a registered package → excluded; a `*.tf` file at depth 4 (`a/b/c/main.tf`: its directory 3 components deep, no `*.tf` above it) → `a/b/c`; a `*.tf` file at depth 5 (`a/b/c/d/main.tf`, no `*.tf` above it) → not proposed; root-level `*.tf` with no `.` record, plus `infra/main.tf` → `.` only; root-level `*.tf` with a `.` record, plus `infra/main.tf` → `infra` (the walk descends past the registered root); two runs → byte-identical output, one path per line, sorted by path.
- `init.yaml`'s bytes are unchanged by a run.
- The `init.yaml` the tests read is produced by `init_helper` setters, not hand-authored.
- The full `tests/lib` suite is green; the python-reviewer loop runs until a review returns no findings.

### Phase 3 — `read-manifests`' `language_hint` (D4 (a))

#### Deliverables

*(amended after the close, 2026-10-07 — amendment A of `### Post-close amendments — 2026-10-07`: `read-manifests` reads `init.yaml`, and `language_hint` is non-null only for a package whose `init.yaml` record has `manifest: null`; that subsection governs the bullets below, Verify included, where they conflict)*

- `_configure/_cmds_read.py` `cmd_read_manifests`: `language_hint` on every entry, per D4 (a), with the extension map as one closed constant.
- Tests in `tests/lib/test_configure_helper.py`.

#### Verify

- Fixtures come from `init_helper` + `index_helper build-index` output, never a hand-authored `index.json`: a null-manifest package of `*.tf` files → `HCL`; of `*.sql` → `SQL`; of `*.yaml` / `*.yml` → `YAML`; mixed `*.tf` and `*.yaml` → the majority, and the map's order on a tie; no mapped extension → `null`; a manifest-bearing package → `null`.
- Under amendment A, fixtures built the same way: a package registered with `--manifest pubspec.yaml` and holding `*.yaml` files → `language_hint: null`; the same tree registered with `--no-manifest` → `YAML`; `init.yaml` deleted, or overwritten with unparseable content, after `build-index` → `read-manifests` exits 0 and every `language_hint` is `null`.
- The existing `read-manifests` tests pass unchanged apart from the added key.
- The full `tests/lib` suite is green; the python-reviewer loop runs until a review returns no findings.

### Phase 4 — `/devforge:init-forge` Step 4 (D2, D3, OQ-3's F19 docs part)

#### Deliverables

- `src/commands/init-forge/main.md` `## Step 4: Discover packages`: the verb call after the manifest walk, the candidate question with D2's three option labels, the free-text declaration, the `add-package --no-manifest` call and D2's hand-back arms.
- `## Outputs of this phase`: the `packages_detected` bullet no longer says only *"empty `[]` for projects without manifests"* — it names `manifest` null for a manifest-less package.
- `## Step 5: Render Summary`: the delegated-values sentence covers Step 4.
- Step 6's per-package bullet, *"For each package, walks the source tree (capped at 500 files), reads the package manifest (…)"* — Phase 4 is its only owner phase: its manifest clause is made true for a null-manifest package, which has no manifest to read (D3); under OQ-3's F19 recommendation, its cap is corrected too — grep `500` in `src/commands/init-forge/main.md` and classify every hit in the commit body (F19). If OQ-3's F19 recommendation is declined, this phase still corrects that bullet's cap clause, *"(capped at 500 files)"*, against `index_helper._MAX_FILES_PER_PACKAGE` as read at build time — the cap clause and the manifest clause are one sentence, and the repo's cross-check rule forbids leaving a known-false clause in a sentence this phase edits.
- `docs/v2/ARCHITECTURE.md`, under OQ-3's F19 recommendation — F19's three stale-cap hits, *"Walk source tree (capped at 500 files; `files_truncated: true` flag set on overflow)."*, the `_concern_input.py` row's *"which caps at 500 files"* clause and the *"**`index_helper` 500-file cap.**"* item, each corrected against `index_helper._MAX_FILES_PER_PACKAGE` as read at build time; grep `500` in the file and classify every hit in the commit body (F19). Only the cap clause of the `_concern_input.py` row changes here; that row's layout wording is Phase 8's, under D1 (a) only.

#### Verify

- `grep -n -e 'no-manifest' -e '<the ratified verb name>' src/commands/init-forge/main.md` hits Step 4.
- The opening sentence *"It performs no classification — no language inference, no framework detection, …"* is re-read and still true: the verb proposes directories and persists no language.
- Every new AskUserQuestion has 2–4 options and no explicit "Other" option; no candidate path is an option; the candidate question's options are exactly D2's three labels, written as a bullet list under the question.
- Step 6's per-package bullet is re-read after the edit and quoted in the commit body as true for a null-manifest package.
- Under OQ-3's F19 recommendation: `grep -n 500` over `src/commands/init-forge/main.md` and `docs/v2/ARCHITECTURE.md` — no hit states a 500-file cap, and every hit is classified in the commit body, one at a time.
- If OQ-3's F19 recommendation is declined: Step 6's per-package bullet, re-read after the edit, states no 500-file cap, and the commit body quotes its corrected cap clause beside `index_helper._MAX_FILES_PER_PACKAGE` as read at build time.
- The instruction-reviewer loop runs until a review returns no findings.

### Phase 5 — `/devforge:configure` Phase 2 rules and Phase 3 per-record override (D4, amendments A–C)

#### Deliverables

*(amended after the close, 2026-10-07 — amendments A, B and C of `### Post-close amendments — 2026-10-07`: the rules key on `INIT_JSON.packages_detected[].manifest` (A); with packages registered but none manifest-bearing, each flat array is the single entry `N/A` (B); and the deliverables widen to configure's `## Phase 3 — Bulk-confirmation prompt` — its echo template, `### Parsing the user reply` and `### Setter mapping` (C); that subsection governs the bullets below, Verify included, where they conflict)*

- `src/commands/configure/main.md`: the `read-manifests` shape sentence names `language_hint`; the `LANGUAGES` and `PACKAGE_STACKS` `language` rules cover a null manifest; the commands rule per D4 (a); the flat arrays per D4 (b); `language` per D4 (c).
- The five `**Per-package**` bullets D4 (b)'s ruling reaches, each edited so it is true for a null-manifest package — which, under (i), has `N/A` in its `PACKAGE_STACKS` record and no entry in the flat arrays: `BUILD_COMMANDS`' *"comma-separated list aligned per-package; each entry is the package's `scripts.build` from `MANIFESTS_JSON.packages[]`."*; `TYPE_CHECK_COMMANDS`' *"comma-separated; per-package `scripts.typecheck` or `scripts.tsc` from `MANIFESTS_JSON`."*; `LINT_COMMANDS`' *"comma-separated; per-package `scripts.lint`. When absent, emit `N/A`."*; `TEST_COMMANDS`' *"comma-separated; per-package `scripts.test`. When absent, emit `N/A`."*; and `PACKAGE_STACKS`' `build_command` / `type_check_command` / `lint_command` bullet, *"same per-package values used by the flat string-arrays above; `test_command` is derived separately (see the next bullet) — it does NOT follow the flat arrays' `N/A`-when-absent rule."*
- Under amendment C, `src/commands/configure/main.md`'s `## Phase 3 — Bulk-confirmation prompt`: the echo template lists each `package_stacks` record as `<path> (<language>)`; `### Parsing the user reply` gains the per-record override form `package_stacks <path> <key>: <value>`; `### Setter mapping` applies those overrides to the composed records before the single `set-package-stacks` call, and recomputes `languages` from the final records when a per-record `language` override was given without a `languages:` line.

#### Verify

- `grep -n language_hint src/commands/configure/main.md` hits the shape sentence and the `language` rules.
- Each of the five bullets listed above is re-read after the edit and quoted in the commit body as true for both a manifest-bearing and a null-manifest package.
- `BUILD_COMMANDS`' *"emit the ecosystem default"* sentence no longer reaches a null-manifest package.
- The existing *"do NOT invent an ecosystem-default guess"* rule is unchanged.
- Under D4 (b) (i): the edited flat-array rules give a null-manifest package no entry, so index 0 — read by `cmd_verify_touched`'s `primary_type_check`, `primary_lint`, `primary_build` and `primary_test` assignments, by `_get_test_command` and by the configure probe (F16) — never holds its `N/A`, except amendment B's all-`N/A` placeholder; the commit body quotes the reworded rules beside those four assignments.
- Under amendment B: when at least one package is registered and none is manifest-bearing, the edited rules make each of `BUILD_COMMANDS`, `TYPE_CHECK_COMMANDS`, `LINT_COMMANDS` and `TEST_COMMANDS` exactly `["N/A"]` — the only case that puts `N/A` at index 0; the commit body quotes that rule.
- Under amendment C: the echo template under `## Phase 3 — Bulk-confirmation prompt` lists each `package_stacks` record as `<path> (<language>)`, and that section's `### Parsing the user reply` defines the `package_stacks <path> <key>: <value>` override line.
- Under amendment C: that section's `### Setter mapping` applies every per-record override to the composed records before the single `set-package-stacks` call, and recomputes `languages` from the final records when a per-record `language` override was given without a `languages:` line.
- Under amendment C: the file's other reply-parsing sections — `### Phase 5.2 — Prune agents`' `#### Parsing the user reply` and `## Phase 6 — Exclude framework folders from project linters`' `### Parsing the user reply` — are untouched; this phase's diff of `src/commands/configure/main.md` changes neither.
- The instruction-reviewer loop runs until a review returns no findings.

### Phase 6 — One concern-root owner, behavior-preserving (D5 (i))

#### Deliverables

- The owner module (working name `_concern_root.py`) under `src/devforge/lib/_generate_docs/`, with its tests, and every F7 site rewritten to call it for the concern-root path only; each site's skip predicate stays as it is (D5 (i), F20). **No output changes.**
- The three layout-embedding messages that the sweep pattern matches (F7) take their path from the owner.
- The owner also exposes a package's root directory, which no site calls in this phase — Phase 7 consumes it for D5 (v).

#### Verify

- **Every existing test module that exercises `_generate_docs/` passes unchanged** — find them by grep at build time; carry no list from this document.
- **A pinning test, written and run against the pre-refactor code, then run again after the refactor:** `_package_input._enumerate_concerns` enumerates a planted `src/static/` and `_preflight._enumerate_concerns` does not; `_preflight._enumerate_concerns` enumerates a planted `src/.x/` and `_package_input._enumerate_concerns` does not (F20).
- `git grep --untracked -n -F -e '"src"' -e "'src'" -e 'src/{' -- src/devforge/lib/_generate_docs/` returns only the owner's lines; any other hit is classified one at a time. ⚠ **`--untracked` is load-bearing: plain `git grep` skips the not-yet-committed owner module (Trap 13).**
- `_validators_decomposition.py`'s *"{1}/src/; run add-concern"* message, which the pattern does not reach, is checked by eye (F7).
- The python-reviewer loop runs until a review returns no findings.

### Phase 7 — The fallback (D5 (ii)–(vi), OQ-2, OQ-5)

#### Deliverables

- The owner gains the fallback root; the walks skip dot-prefixed directories under the fallback root; `_walk_concern_subfolder` and `_enumerate_immediate_dirs` test only path components below the package root, taken from the owner's Phase 6 accessor — `_enumerate_immediate_dirs` gains the package-root parameter D5 (v) states, filled by `_preflight._diff_concern` and `_concern_input.cmd_concern_input` (D5 (v)); `_collect_src_root_files` yields nothing for a fallback package (D5 (vi)); OQ-2's name; OQ-5's exclusion, with preflight's prefix, if ratified; tests.
- The `src/` layout statements in the docstrings, comments and user-facing messages under `src/devforge/lib/_generate_docs/`. Under D5 (ii) a fallback concern is rooted at `<pkg>/`, so `<pkg>/src/<concern>/` stops being the only layout; no other phase owns these statements — Phase 6's sweep pattern returned no docstring or comment on 2026-10-07 (F7), and Phase 8 edits markdown only. Once the rest of this phase's code is written, run `git grep --untracked -n 'src/' -- src/devforge/lib/_generate_docs/` (Trap 13) and classify every hit in the commit body, one at a time, as exactly one of: owner code (a code line of the owner module, never one of its docstrings or comments); edited (a docstring, comment or user-facing message this phase edits so it describes both layouts); still true (a docstring, comment or user-facing message true of the post-fallback code as written — e.g. one that describes the `src/` case explicitly); unrelated (a hit that describes no concern or package layout — the known one is `_doc_setters/_cmds_project.py`'s `--entry-points` help example, `"path": "src/main.ts"`). A user-facing message is classified by its text, wherever its path comes from. A code line outside the owner module that still computes a `src/` path fits no class: this phase routes it through the owner, after which the grep no longer returns it. The grep's output at build time is the set to classify; the docstrings that follow are known examples describing the `src/` layout on 2026-10-07, not the full set, each classified like any other hit: `_concern_input.py`'s module-docstring output-shape examples, `"subfolder": "<package>/src/<concern>/"` and `"subfolder": "<package>/src/<concern>/<child>/"`; `_setters_concern.py` `_check_tree_entry_coverage`'s *"Derives the expected subfolder as \"src/<concern_name>\""* and `_count_rendered_tree_entries`' example header, *"(e.g., \"src/components/\")"*; `_package_input.py` `_enumerate_concerns`' *"List direct subdirs of `<project_root>/<pkg>/src/`. Sorted alphabetical."*; `_validators_decomposition.py` `_check_decomposition`'s *"When `src/` exists, every …"*. A baseline, never an expected count: `git grep -n 'src/' -- src/devforge/lib/_generate_docs/` returned 35 lines across 10 files on 2026-10-07, before Phase 6 routes the F7 sites through the owner — `_concern_input.py` 6, `_doc_setters/_cmds_project.py` 1, `_doc_setters/_renderers.py` 2, `_package_input.py` 3, `_preflight.py` 5, `_setters_concern.py` 5, `_setters_concern_files.py` 1, `_validate_doc.py` 5, `_validators_concern.py` 2, `_validators_decomposition.py` 5; classify the hits the grep returns at build time.

#### Verify

- A planted Terraform package without `src/` — `infra/tf` with `main.tf`, `variables.tf`, `modules/vpc/main.tf` and a `.terraform/` subtree — registered through Phase 1's flag and indexed by `build-index`: preflight enumerates exactly one concern for it; `concern-input` lists its `*.tf` files and nothing under `.terraform/`; `init-doc` → render → `validate-doc` cite-backs resolve; the three `index.json`-prefix sites (`_setters_concern.py`, `_setters_concern_files.py`, `_validators_concern.py`) see the package's files; `package-input` exits 0 and its `concern_seeds` carry that same one concern; the decomposition validator passes.
- For that package, `package-input` prints `"src_root_files": []`, a direct `_collect_src_root_files` call returns two empty lists, and two consecutive `package-input` runs on unchanged input print the same `source_stamp` (D5 (vi)). The stamp is a hash, so the absence of a `src-root` part is pinned through those two checks, never by reading the stamp.
- Two further planted packages, each registered through `init_helper add-package` and indexed by `build-index`: a fallback package at `infra/build`, and a `src/`-layout package at `packages/assets` with `src/ui/` — `concern-input` exits 0 and lists a non-empty file set for each one's concern (D5 (v), F21).
- A large flat package with at least two immediate child directories takes the split path.
- `.` unchanged: a standalone `.` with no `src/` yields zero concerns; a monorepo `.` is still skipped.
- An existing `src/`-layout package whose path holds no `_TRIVIAL_LEAF_DIRS` name produces output byte-identical to Phase 6's.
- Under OQ-5 = exclude: a nested registered package's files are absent from the fallback concern, in a standalone fixture and in a wrapper fixture whose `index.json` `project_root` differs from the install root.
- `git grep --untracked -n 'src/' -- src/devforge/lib/_generate_docs/` (Trap 13): every hit is classified in the commit body, one at a time, as owner code, edited, still true or unrelated; every hit classified owner code is a code line of the owner module.
- No docstring or comment among that grep's hits states the `src/` layout as the only layout.
- The full `tests/lib` suite is green; the python-reviewer loop runs until a review returns no findings.

### Phase 8 — Layout statements sweep (D5)

#### Deliverables

Each statement below is re-read against the post-Phase-7 code, and its classification — edited / still true — is recorded in the commit body:
- `src/commands/generate-docs/main.md` — *"(rooted at `<pkg>/src/<concern>/<sub_name>/`)"* and *"Loose files at `<P>/src/` root"*.
- `src/CLAUDE.md` `## Artifact Storage` — *"# One subdir per src/ subfolder"*.
- `src/agents/tech-writer.md` — the same comment, and *"New concern (a new `src/` subfolder)"*.
- `src/devforge/storage-rules.md` — *"# One subdir per src/ subfolder concern"*, *"Concern dirs use the source-subfolder name verbatim"* and *"Concerns are derived from `src/` subfolders enumerated by /devforge:init-forge's index.json"*.
- `docs/v2/ARCHITECTURE.md` — the `_concern_input.py` row's layout wording (*"Walks `<pkg>/src/<concern>/` filesystem-direct"*), plus a row for the owner module. Under OQ-3's F19 recommendation, Phase 4 already corrected that row's cap clause (F19); this phase does not touch it. If OQ-3's F19 recommendation is declined, this phase also corrects that row's cap clause, *"which caps at 500 files"*, against `index_helper._MAX_FILES_PER_PACKAGE` as read at build time — the layout wording and the cap clause are one sentence, and the repo's cross-check rule forbids leaving a known-false clause in a sentence this phase edits.

#### Verify

- `grep -n 'src/' <each file above>` — every hit classified as edited, still true or unrelated, **one at a time.**
- If OQ-3's F19 recommendation is declined: the `_concern_input.py` row of `docs/v2/ARCHITECTURE.md`, re-read after the edit, states no 500-file cap, and the commit body quotes its corrected cap clause beside `index_helper._MAX_FILES_PER_PACKAGE` as read at build time.
- The instruction-reviewer loop runs until a review returns no findings.

### Phase 9 — Docs and ledgers

#### Deliverables

- `CHANGELOG.md` — one entry under whichever unreleased section is in flight, **re-verified live at build time**, never inside a released version block. It states the evidence class and never says a consumer validated the fix.
- `DEVELOPMENT-STATUS.md` — the ledger line.
- `PLAN-STATUS-ARCHIVE.md` — this plan's `## Index` line and its `## Entries` record — both, in the same commit.
- `FINDINGS.md` — the entries OQ-3 ruled; under OQ-3's F20 / F21 ownership rule, that includes the F20 / F21 entry exactly as the Phase 0 close record states its case.
- Under D1 (c): the new Gate 2 stub.
- This plan's `**Status**:` line — rewritten from the build record, `git log --oneline --grep 'plan-112'`.
- The root `CLAUDE.md` router — grep it for each new identifier (`--no-manifest`; `language_hint`; the ratified verb name, working name `detect-manifest-less`; under D1 (a), the owner module's name, working name `_concern_root.py`) and record the grep result in the ledger line.

#### Verify

- Each file is staged by explicit path, and `git diff --cached --stat` shows only these files.
- On every markdown edit, the instruction-reviewer loop runs until a review returns no findings.

### Phase 10 — Consumer e2e (user-driven HARD GATE, DEFERRED)

Run by the maintainer, on a consumer install the maintainer picks — **never the frozen benchmark install** — through the setup chain on a monorepo with Terraform directories.

#### Verify — anchors

- (a) Step 4 proposes the Terraform directories.
- (b) `.devforge/index.json` carries them with `manifest_file: null`.
- (c) Under D1 (a): `/devforge:generate-docs` writes concern and package docs for them. Under (b) or (c): RECORD ONLY — none are expected.
- (d) `/devforge:configure`'s `PACKAGE_STACKS` records them with `HCL` and no commands, and index 0 of the flat arrays is not theirs (except amendment B's all-`N/A` placeholder).
- (e) A `.tf` edit in `/devforge:implement` matches its package in `verify-touched`.

**Until this phase runs, "built and build-verified" is the ceiling of every claim this plan makes.**

---

## Non-goals

- **Any `PROJECT_NATURES` change.** `devops-engineer` is never pruned (F13).
- **Editing plan 101.** It is closed (F9).
- **Touching `detect_report.py`.** It is orphaned and says *"do NOT extend it"* (F5).
- **Unifying the three manifest lists** (F3) — plan 118's territory.
- **Terraform command defaults** (D4 (a)).
- **The bare-name `target` skip** — plan 113.
- **Command cwd for per-package commands** — plan 116.
- **Any codebase-graph change** — the graph already sees Terraform (F14).
- **F15's `.` matching** — recorded per OQ-3, never fixed here.
- **Unifying the two concern enumerations' skip rules** (F20) — Phase 6 preserves both unchanged (D5 (i), Trap 15); F20 is recorded per OQ-3's F20 / F21 ownership rule, never fixed here.
- **Mechanical detection of SQL or workflow-YAML packages** — no reliable signal; D2 gives them the operator route.
- **Nothing is done to any installed consumer** outside Phase 10, and nothing at all to the frozen benchmark install.

---

## Context for next session

⚠ **Evidence class, repeated: ONE consumer observation, with NO artifact of it in this repo and NOTHING measured; plus one PLANTED codebase-graph probe (F14) and direct helper calls (F12, F15), all 2026-10-07. Every other statement is a read of this tree on 2026-10-07.** ⚠ All line digits drift — **grep the quoted text, never the digits.**

**The one sentence that governs everything here:** **a manifest-less directory is kept out by TWO gates — registration (an LLM instruction) and the `<pkg>/src/` layout (11 hardcoded sites) — and fixing the first alone still leaves it without docs.**

### Honest bounds

- **One observation, of the symptom only.** The run showed missing docs for Terraform directories; Gate 2 is a code read (F6), not an observation (`## Origin & evidence`). Nothing is known here about the observed project's layout.
- **D2's shallowest-directory rule and D5's single concern rest on a Terraform-domain convention** — a root module keeps its `*.tf` files at its own directory root (a Terraform-domain claim, NOT a tree fact).
- **F14 is one planted probe on one graph version.** HCL and YAML were indexed; the SQL procedure was NOT extracted. No other version and no real project were tested.
- **D5 changes output for existing installs** with flat-layout non-`.` packages: new docs appear where none existed. Under D5 (v) it also changes output for `src/`-layout packages whose path holds a `_TRIVIAL_LEAF_DIRS` name: their concerns gain the files the walk drops today (F21).
- **A root holding `*.tf` files still gets no docs.** D2's verb proposes `.` for it when no `.` record exists, `.` registers with `manifest: null`, and D5 (iii) keeps `.` on the `src/` requirement — so a pure-Terraform standalone repo whose root module sits at the project root yields zero concerns. A residual of this plan, recorded, not fixed.
- **D4 leaves infra edits unverified, silently.**
- **A root-level `*.tf` edit does not reach a manifest-less `.` record** — a code read added at Phase 9, not run. D2's verb proposes `.` when the root holds a `*.tf` file and no `.` record exists, and `.` registers with `manifest: null`; D4 (b) (i) then gives it no entry in the flat command arrays, so where another registered package is manifest-bearing, index 0 belongs to that package. `_match_package` never matches a `.` record (F15), so a touched root-level `*.tf` file takes the primary-stack fallback and runs that package's index-0 commands — D4 (a)'s *"matches its own package by F12's longest-prefix rule and runs nothing"* does not hold for `.`. Where every registered package is manifest-less, amendment B's `N/A` placeholder makes the fallback run nothing. Recorded, not fixed: `FINDINGS.md` entry 13.
- **A project with ZERO registered packages still composes empty flat arrays.** The per-package alignment rules (F10) give it no entry, before this plan as after it; amendment B's `N/A` placeholder covers a project whose registered packages are all manifest-less, not one with none (`### Post-close amendments — 2026-10-07`). Pre-existing, and not addressed by this plan.
- **Plans execute in numeric order.** When this plan's Phase 0 closes, read each lower-numbered open plan's `**Status**:` line before building; **do not carry a count of them from this document.**

### Traps

**Trap 1 — digits drift.** Every quote here is grep-able; no digit is trusted.

**Trap 2 — three manifest lists** (F3). A builder who "fixes" one list here creates the drift plan 118 exists to remove.

**Trap 3 — `.` is special in three places:** preflight skips it in a monorepo (F6); `_match_package` never matches it (F15); D5 (iii) keeps it on `src/`.

**Trap 4 — standalone installs keep forge artifacts at the project root** (D5 (iii)). A fallback for `.` would document `specs/` and `docs/` as concerns.

**Trap 5 — the emitter drops unknown record keys** (F2). Any record field beyond `path` and `manifest` vanishes on the next re-emit unless `emit_yaml` changes.

**Trap 6 — `_PACKAGES_DETECTED_PATH_RE` reads `init.yaml` by regex** (F5). A `manifest: null` line does not affect it — re-verify at build (Phase 1).

**Trap 7 — test fixtures come from the real producer chain:** `init_helper` setters → `init.yaml` → `index_helper build-index` → `index.json` → the consumer under test. Never a hand-authored `init.yaml` or `index.json`.

**Trap 8 — `.terraform/` in the concern walk** (F17). The fallback root makes the hidden-dir non-skip live; D5 (iv) closes it.

**Trap 9 — index 0 of the flat command arrays** (F16). An `N/A` there disables the primary-stack fallback, the regression gate's test command and the configure probe's primary check — the outcome D4 (b) (i) keeps a null-manifest package from causing (except amendment B's all-`N/A` placeholder).

**Trap 10 — two file sets.** The prefix sites read `index.json`'s `files[]` (hidden directories and `_FILE_WALK_SKIP_DIRS` excluded); the walk sites rglob the filesystem with only the trivial-leaf filter, applied to the full project-relative path (F7, F17, F21). They already differ; the fallback root widens the gap.

**Trap 11 — "the run observed residual 12."** It did not (D1). A summary that says so falsifies the evidence class.

**Trap 12 — public repo.** No client, install, repo, ticket or session identifier — including any name read from a code comment or docstring in this tree. It binds every commit body and every grep-classification step in this plan as much as this file's own text: a hit that carries such a name is classified without quoting the name.

**Trap 13 — `git grep` skips untracked files.** A Verify grep over a module created in the same phase reads empty until that module is committed — run every such grep with `--untracked`.

**Trap 14 — basename collisions in `/devforge:constitute`'s package-name map** (F11). Many registered Terraform directories (`envs/dev`, `envs/prod`, …) add basenames that may collide with other packages'; the map keeps the last record.

**Trap 15 — do not merge the two enumerations' skip rules in Phase 6** (F20). `_package_input._enumerate_concerns` and `_preflight._enumerate_concerns` skip different names — `src/static/` is a concern for one and not the other. Merging them changes output on existing installs and breaks Phase 6's behavior-preserving contract; Phase 6's pinning test catches it.

**Trap 16 — the trivial-leaf filter sees the package's own path components** (F21). `_walk_concern_subfolder` and `_enumerate_immediate_dirs` test the full project-relative path, so a package at `infra/build` or `packages/assets` loses every file. A fixture whose package path holds no `_TRIVIAL_LEAF_DIRS` name never shows it — D5 (v) closes it, and Phase 7's `infra/build` and `packages/assets` fixtures pin it.

### File anchors

**EDIT targets** — a phase of this plan writes each:
- `src/devforge/lib/init_helper.py` — `build_parser`, `cmd_add_package`, `_render_summary` (Phase 1); the detection verb (Phase 2). Tests: `tests/lib/test_init_helper.py`.
- `src/devforge/lib/index_helper.py` and `src/devforge/lib/_generate_docs/_concern_input.py` — module-docstring lines only, under OQ-3 (Phase 1, every D1 outcome, F19): `index_helper.py`'s 500-cap line, and the sentences of `_concern_input.py`'s *"Why filesystem and not index.json:"* paragraph that Phase 1's re-read classifies as edited.
- `tests/lib/test_index_helper.py`, `tests/lib/test_configure_helper.py` — the chain tests (Phases 1, 3).
- `src/devforge/lib/_configure/_cmds_read.py` — `cmd_read_manifests` (Phase 3).
- `src/commands/init-forge/main.md` — Step 4, `## Outputs of this phase`, Step 5, and Step 6's per-package bullet: its manifest clause (D3) and its cap clause, under OQ-3's F19 recommendation and when it is declined (Phase 4).
- `src/commands/configure/main.md` — Phase 2's composition rules, the `read-manifests` shape sentence and, under amendment C, `## Phase 3 — Bulk-confirmation prompt`'s echo template, `### Parsing the user reply` and `### Setter mapping` (Phase 5).
- `src/devforge/lib/_generate_docs/` — the new owner module and `_preflight.py`, `_concern_input.py`, `_package_input.py`, `_setters_concern.py`, `_setters_concern_files.py`, `_validators_concern.py`, `_validate_doc.py`, `_validators_decomposition.py` (Phases 6–7, D1 (a) only). Phase 7 also edits every docstring, comment and user-facing message that its `src/` grep classifies as edited, in these modules and in every other module under `src/devforge/lib/_generate_docs/` that the grep reaches — its 2026-10-07 baseline reaches two more, `_doc_setters/_renderers.py` and `_doc_setters/_cmds_project.py`.
- `docs/v2/ARCHITECTURE.md` — F19's three stale-cap hits, under OQ-3 (Phase 4, every D1 outcome).
- `src/commands/generate-docs/main.md`, `src/CLAUDE.md`, `src/agents/tech-writer.md`, `src/devforge/storage-rules.md`, `docs/v2/ARCHITECTURE.md` (Phase 8, D1 (a) only; in `docs/v2/ARCHITECTURE.md`, the `_concern_input.py` row's layout wording — and that row's cap clause if OQ-3's F19 recommendation is declined — and the owner-module row).
- `CHANGELOG.md`, `DEVELOPMENT-STATUS.md`, `PLAN-STATUS-ARCHIVE.md`, `FINDINGS.md`, the root `CLAUDE.md` router, and this plan's `**Status**:` line (Phase 9).

**READ-ONLY anchors** — read, never edited by this plan, except where an entry names its exception:
- `src/devforge/lib/index_helper.py` — `cmd_build_index`, `_build_package_record`, `_list_package_files`, `_MANIFEST_REGISTRY`, `_MAX_FILES_PER_PACKAGE` (F3, F4, F19); read-only except the Phase 1 docstring line listed under EDIT targets.
- `src/devforge/lib/_implement/_cmds_verify.py` — `_match_package` and `cmd_verify_touched`'s primary fallback, its `primary_*` assignments (F12, F15, F16).
- `src/devforge/lib/_verify/_regression.py` `_get_test_command`; `src/devforge/lib/_configure/_validators.py`'s executability probe (F16).
- `src/devforge/lib/_configure/_cmds_set.py` `cmd_set_package_stacks` (F10); `src/devforge/lib/_configure/_render.py` (F10, F13, F16); `src/devforge/lib/_configure/_hints.py` (F10).
- `src/devforge/lib/_constitute/_validate_metrics.py` `_build_package_name_map` (F11).
- `src/devforge/lib/_generate_docs/_validators_package.py` `_PACKAGES_DETECTED_PATH_RE` (F5).
- `src/devforge/lib/detect_report.py` — orphaned (F5).
- `src/agents/devops-engineer.md` (F13).
- `101-NON-WEB-STACK-READINESS-PLAN.md` — F26, F36, OQ-5, residual 12 (F9). **Closed; frozen.**
- The stubs `113-…` (Index Skip-List), `116-…` (Configure Workspace Commands), `118-…` (Mechanical Stack Detection).

---

## When resuming work

1. **Read this plan in full** before touching anything. Find any sibling plan by its TITLE.
2. **Re-run `git status --short` and classify every changed file as yours or another session's** — another session may share the checkout. Never stage a file you did not change.
3. **Check `### Phase 0 close record`.** While its opening line does not read CLOSED, nothing builds; it reads *CLOSED 2026-10-07* now. Quote the ratified outcomes from the record and from the `### Post-close amendments — 2026-10-07` subsection, which overrides the close record where they conflict; never quote them from a decision's drafting text — that text keeps the options not taken.
4. **Re-verify F1–F21 by grepping their quoted text**, never by digits: `Step 4: Discover packages`, `use your knowledge of which ecosystem uses which`, `required=True`, `Closed enum — do not expand at runtime`, `_MANIFEST_REGISTRY`, `"manifest_file": None`, `skipped silently`, `has no \`src/<concern>/\` subdirs`, `some ecosystems use a flat package layout`, `Hidden dotfile-prefixed dirs are NOT skipped`, `missing required field 'language'`, `Only the FIRST entry of each primary array is probed`, `type_check_commands[0] if type_check_commands else None`, `sort_keys=True`, `applies_to: ["all"]`, `capped at 500 files`, `capped at 500)`, `500 entries per package`, `name in ("node_modules", "dist", "build", "target")`, `Return True if any path component of rel_path is a trivial-leaf dir.`, and F7's three-pattern sweep. ⚠ **Use `git grep -n` for every site under `src/` or `tests/`** — a plain recursive grep also matches compiled `__pycache__` files. ⚠ **F12, F14 and F15 are runs, not reads:** re-derive F12 and F15 with a direct `_match_package` call; F14 is re-derivable only by planting a new scratch repo.
5. **Then check each lower-numbered open plan's `**Status**:` line** — plans execute in numeric order.
6. **Build in `## Phases` order**, each phase through its route, each committed by explicit path.
7. **After each phase, cross-check:** grep every name the phase touched — `--no-manifest`, the ratified verb name, `language_hint`, the owner module's name, `manifest: null`, `src/` in `src/devforge/lib/_generate_docs/` (Phase 7) and in the Phase 8 files — and fix any dangling reference in the SAME change. ⚠ **In `CHANGELOG.md`, in finished plans and in plan 101, those strings are frozen records — never edited.**
8. **Keep the evidence class attached.** Any summary of this plan repeats it: **ONE consumer observation, with NO artifact of it in this repo and NOTHING measured; plus one PLANTED codebase-graph probe (F14) and direct helper calls (F12, F15).**
