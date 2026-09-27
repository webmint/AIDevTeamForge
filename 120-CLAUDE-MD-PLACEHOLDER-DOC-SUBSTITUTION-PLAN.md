# 120 — CLAUDE.md Placeholder Doc Substitution Plan

**Created**: 2026-09-25
**Updated**: 2026-09-26
**Status**: Stub — problem statement, origin and findings (F1–F6). The rest of the plan body (decisions, phases) is to be authored; no fix is chosen.

## Problem

`substitute-templates` also substitutes the example markers inside the explanatory sentence of the installed `CLAUDE.md` that describes `{{UPPERCASE}}` placeholders, so after `/devforge:configure` the sentence shows the project's real values as its "examples" of placeholders.

## Origin

Observed during a full setup-chain run (`/devforge:init-forge` → `/devforge:generate-docs` → `/devforge:configure` → `/devforge:constitute`) on a wrapper install over an npm-workspaces Node/TypeScript monorepo with Terraform-only packages.

Observed again, independently, during a setup-chain run on a Unity game project, reported 2026-09-25: the installed `CLAUDE.md`'s `## Placeholder Convention` sentence showed the project's name and the languages `C#, ShaderLab, Python, Bash` as its examples, and a manual run-sheet check, `grep -c "{{" CLAUDE.md`, returned `2` where the sheet expected `0`. The two observations are on a web monorepo and a game engine project, so the defect does not depend on the project's nature (F2: both example markers are keys `_build_substitution_map` sets for every project).

## Findings

F1–F6 were verified against the tree by the orchestrator on 2026-09-26. ⚠ **Line digits drift — grep the quoted text, never the digits.**

**F1 — Only one template carries the prose.** `src/CLAUDE.md` `## Placeholder Convention`: line 207 reads ``Any `{{UPPERCASE}}` marker (e.g., `{{PROJECT_NAME}}`, `{{LANGUAGE}}`) in a template file is a substitution placeholder. …``; line 209 reads ``… Readers must never see literal `{{...}}` text in substituted output; if a placeholder reaches the user verbatim, the substitution step is broken or the marker name is wrong.`` A grep over `src/` for `{{UPPERCASE}}` / `{{...}}` finds only `src/CLAUDE.md` and `src/devforge/lib/_configure/_render.py`; the `_render.py` hits are the Category D passthrough (F3), not a template.

**F2 — Why the examples are substituted (the Problem's mechanism).** `_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")` at `src/devforge/lib/_configure/_render.py:221` matches every uppercase-key marker, including `{{PROJECT_NAME}}` and `{{LANGUAGE}}` inside the prose. Both are real keys in the map `_build_substitution_map` (`_render.py:282`) builds, and it sets both for every project: `PROJECT_NAME` is a Category A pass-through (the function sets every `_PROJECT_CONFIG_KEY_ORDER` key, as `""` when the config value is null), and `LANGUAGE` is a Category B singular alias (`_SINGULAR_ALIASES`) that renders `LANGUAGES` comma-joined, which is the `C#, ShaderLab, Python, Bash` of the second Origin observation. So both are replaced with the project's values.

**F3 — Why two `{{` lines survive (the second symptom).** `{{UPPERCASE}}` on line 207 survives on purpose: `_build_substitution_map`'s "Category D: identity passthrough" maps it to itself (`sub_map["UPPERCASE"] = "{{UPPERCASE}}"`, `_render.py:343-344`), so the renderer does not treat it as an unknown key. `{{...}}` on line 209 survives because `...` does not match `[A-Z_]+`. Every other `{{` in `src/CLAUDE.md` is an uppercase key marker, which an exit-0 run replaces. `grep -c` counts LINES, so the result is 2 — the rendered forms of source lines 207 and 209 (their rendered line numbers can differ: `{{PACKAGE_STACKS_SECTION}}` at line 33 renders a multi-line table). The rendered file is therefore half-substituted prose: the examples carry project values while the pattern name and the ellipsis stay literal.

**F4 — The framework's contract text is false for `CLAUDE.md`.** `src/commands/configure/main.md:17` (``- `CLAUDE.md` — substituted in place; no `{{KEY}}` markers remain.``), `src/commands/configure/main.md:430` (``- Exit 0 → every template substituted; no `{{KEY}}` markers remain.``) and the `cmd_substitute_templates` docstring at `src/devforge/lib/_configure/_cmds_render.py:104` (`Exit 0 = all templates substituted; no {{KEY}} markers remain.`) all claim no `{{KEY}}` marker remains — but `{{UPPERCASE}}` is a `{{KEY}}`-shaped marker and remains after exit 0. `src/commands/configure/main.md:526` (Phase 7) rests on the same premise to explain why `verify` skips re-scanning: ``Scope note: `verify` does NOT re-scan `CLAUDE.md` or `.claude/agents/*.md` for remaining `{{KEY}}` markers. Template-substitution completeness is enforced by Phase 5's `substitute-templates` exit 0; if Phase 5 succeeded, the templates are clean. …`` — and F3 shows that premise ("if Phase 5 succeeded, the templates are clean") is false for `CLAUDE.md`. And `src/CLAUDE.md:209` itself shows the reader the literal `{{...}}` it says readers must never see. ⚠ `src/commands/configure/main.md:15` makes the same claim for `.claude/agents/*.md` and is TRUE (no agent source carries the prose — F1).

**F5 — The framework's own checks are not affected; manual checks are.** `update.sh:895-897` already says the renderer *"knows {{UPPERCASE}} is an identity passthrough, so a clean file exits 0 — do NOT grep for {{...}} here (that would false-positive on {{UPPERCASE}})."* So `update.sh` relies on the renderer's exit status, not on grep. The only other `{{` grep in `update.sh` — `grep -q '{{[A-Z_]*}}'` at `:976` — runs on a newly installed agent file, and no agent source carries the prose (F1). A human or a run sheet that follows F4's contract text and greps for `{{` gets a false positive. A check that is correct today: `grep -oE '\{\{[A-Z_]+\}\}' CLAUDE.md | grep -vcx '{{UPPERCASE}}'` → expected `0` (it still does not count `{{...}}`, which is not a key). ⚠ `grep -c` exits 1 when it prints `0`, so on a clean file the pipeline exits 1 and on a leftover key it exits 0 — read the printed count, not `$?`.

**F6 — No test renders the real `src/CLAUDE.md`.** `tests/lib/test_configure_helper.py` round-trips the REAL `src/docs/overview.md` / `architecture.md` stubs through `substitute-templates` via `_copy_real_docs_stub` (`:4467`), but every `CLAUDE.md` in that file is written by `_write_claude_md` (`:4279`) with a synthetic string, never the real `src/CLAUDE.md`. No file under `tests/` round-trips the real `src/CLAUDE.md` through `substitute-templates`: a grep over `tests/` for `src/CLAUDE.md` / `"src" … "CLAUDE.md"` finds only docstring mentions in `tests/lib/_finalize/test_preflight.py:26` and `tests/lib/_verify/test_preflight.py:21`, unrelated to substitution, and the only other renderer test file, `tests/lib/_configure/test_substitute_file.py` (the `substitute-file` verb), does not load it either. So the suite never exercises the `## Placeholder Convention` prose, which is why the defect surfaced only in the field (Origin). `test_uppercase_identity_placeholder_round_trips` (`test_configure_helper.py:4440`) pins Category D (F3) with the synthetic line `See {{UPPERCASE}} convention for details.`

## Cross-references a fix must reconcile

No fix shape is chosen. Whatever the fix, each site below must end consistent with it:

- `src/CLAUDE.md:207,209` — the prose (F1).
- `src/devforge/lib/_configure/_render.py:221` — `_PLACEHOLDER_RE` (F2).
- `src/devforge/lib/_configure/_render.py:343-344` — Category D, the `UPPERCASE` identity passthrough, with its docstring entry at `:301-302` (F3). A fix to the prose may make it removable, or may not — NOT decided.
- `src/commands/configure/main.md:17,430` — the "no `{{KEY}}` markers remain" contract text (F4).
- `src/commands/configure/main.md:526` — the Phase 7 scope note's "verify need not re-scan" rationale (F4); whether `verify`'s scope changes is NOT decided.
- `src/devforge/lib/_configure/_cmds_render.py:104` — the same claim in the `cmd_substitute_templates` docstring (F4).
- `update.sh:895-897` — the comment names the passthrough (F5).
- `tests/lib/test_configure_helper.py:4440` — `test_uppercase_identity_placeholder_round_trips` pins Category D (F3), so a fix that changes the passthrough must reconcile it (F6).
