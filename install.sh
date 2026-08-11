#!/bin/bash
# install.sh — Install AIDevTeamForge template into a target project directory.
#
# Responsibility: copy files and create directory structure. Nothing more.
# All project detection and configuration happens in the 4-command sequence
# (run later, inside the target, by Claude Code, in this order):
#
#   /devforge:init-forge      — bootstrap: 5 structural fields + index.json
#   /devforge:generate-docs   — deep codebase scan → docs/ knowledge base
#   /devforge:configure       — populate config + substitute templates + prune agents
#   /devforge:constitute      — synthesize constitution.md
#
# Each command can be re-run independently. install.sh just lays the
# framework files down — wrapper-mode detection, packages_detected,
# .gitignore updates, agent pruning, etc. all happen during the
# command sequence.
#
# Usage:
#   install.sh <target-directory>

# ── Resolve the template repo path (where this script lives) ───────────────
TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$TEMPLATE_DIR/scripts/constitution-drift-check.sh"
. "$TEMPLATE_DIR/scripts/devforge-state-migrate.sh"

# ── Parse arguments ────────────────────────────────────────────────────────
TARGET_DIR=""
ONLY_CMD=""   # --only <command>: surgical single-command delivery (see below)

while [ $# -gt 0 ]; do
  case "$1" in
    --only)
      ONLY_CMD="${2:-}"
      shift
      if [ "$#" -gt 0 ]; then shift; fi
      ;;
    --only=*)
      ONLY_CMD="${1#--only=}"
      shift
      ;;
    -*)
      echo "Unknown flag: $1"
      exit 1
      ;;
    *)
      if [ -z "$TARGET_DIR" ]; then
        TARGET_DIR="$1"
      else
        echo "Unexpected argument: $1"
        exit 1
      fi
      shift
      ;;
  esac
done

# ── Validate target directory ──────────────────────────────────────────────
# Refuse to install into the current directory as a safety guard — users
# should pass an explicit target path.
if [ -z "$TARGET_DIR" ] || [ "$TARGET_DIR" = "." ]; then
  echo "Usage: install.sh <target-directory>"
  echo ""
  echo "Example:"
  echo "  ./install.sh ~/Projects/my-app"
  exit 1
fi

# Target must exist — users create it first (empty dir is fine).
if [ ! -d "$TARGET_DIR" ]; then
  echo "Directory '$TARGET_DIR' does not exist. Create it first."
  exit 1
fi

# ── Python 3 preflight ─────────────────────────────────────────────────────
# Install-time generators (scripts/generate.sh → generate-agents.py /
# emitters) and the wizard-time Detection Report composer
# (.devforge/lib/detect_report.py) all require Python 3. Surface the
# dependency now rather than letting it fail mid-install. Resolve ONE
# interpreter command here and reuse it everywhere below (the --only branch
# and the post-generate stale-command cleanup, both further down) instead of
# re-detecting independently at each call site.
PY_CMD=""
if command -v python3 >/dev/null 2>&1; then
  PY_CMD="python3"
elif command -v py >/dev/null 2>&1; then
  PY_CMD="py -3" # Windows Python launcher routes to 3.x
elif command -v python >/dev/null 2>&1 && [ "$(python -c 'import sys; print(sys.version_info[0])' 2>/dev/null)" = "3" ]; then
  PY_CMD="python" # bare python is 3.x
else
  echo "AIDevTeamForge requires Python 3 on the target machine." >&2
  echo "Install Python 3.8+ (https://www.python.org/downloads/) and re-run." >&2
  exit 1
fi

# ── Surgical mode: --only <command> ────────────────────────────────────────
# Patch an EXISTING install with a single command + its helper subpackage.
# Delivers ONLY the emitted command (.claude/commands/devforge/<cmd>.md +
# .devforge/command-refs/<cmd>/), its helper (.devforge/lib/_<cmd>/ +
# <cmd>_helper{,.py}), and the shared helper package (.devforge/lib/_shared/)
# that refactored helpers import — no agents, no other commands, no
# config/hooks, no full .devforge copy. Use it to push one command's changes
# to a dev/test install without dragging in unrelated work.
if [ -n "$ONLY_CMD" ]; then
  if [ ! -d "$TARGET_DIR/.devforge" ] || [ ! -d "$TARGET_DIR/.claude" ]; then
    echo "error: --only patches an EXISTING install, but '$TARGET_DIR' has no .devforge/ + .claude/." >&2
    echo "  Run a full install first:  ./install.sh '$TARGET_DIR'" >&2
    exit 1
  fi

  echo "Surgical install: delivering only '$ONLY_CMD' into $TARGET_DIR"

  # Emit just this command. claude.py --only validates it is a promoted command
  # and exits non-zero (emitting nothing) if not. Reuses PY_CMD resolved by the
  # module-level Python 3 preflight above.
  if ! $PY_CMD "$TEMPLATE_DIR/scripts/emitters/claude.py" \
       --src "$TEMPLATE_DIR/src" --target "$TARGET_DIR" --only "$ONLY_CMD"; then
    echo "error: emit failed for '$ONLY_CMD' (not a promoted command?)." >&2
    exit 1
  fi

  # Clean up the pre-move flat layout for this one command, if present (plan
  # 63 namespace move) — fail-soft, absent paths are a benign no-op. Without
  # this, a surgical delivery would leave a stale flat duplicate alongside the
  # freshly emitted devforge/-namespaced command.
  if [ -f "$TARGET_DIR/.claude/commands/$ONLY_CMD.md" ] || [ -d "$TARGET_DIR/.claude/commands/$ONLY_CMD" ]; then
    rm -f "$TARGET_DIR/.claude/commands/$ONLY_CMD.md" 2>/dev/null || true
    rm -rf "$TARGET_DIR/.claude/commands/$ONLY_CMD" 2>/dev/null || true
    echo "  removed stale: .claude/commands/$ONLY_CMD.md (+ references/, pre-move layout)"
  fi

  # Copy the command's helper subpackage + launcher, if any. Command name maps
  # to helper paths by replacing hyphens with underscores (audit → _audit /
  # audit_helper; pr-review → _pr_review / pr_review_helper).
  cmd_u="$(printf '%s' "$ONLY_CMD" | tr '-' '_')"
  helper_found=false
  if [ -d "$TEMPLATE_DIR/src/devforge/lib/_${cmd_u}" ]; then
    rm -rf "$TARGET_DIR/.devforge/lib/_${cmd_u}"
    cp -R "$TEMPLATE_DIR/src/devforge/lib/_${cmd_u}" "$TARGET_DIR/.devforge/lib/_${cmd_u}"
    echo "  helper subpackage: .devforge/lib/_${cmd_u}/"
    helper_found=true
  fi
  # Ship the shared helper package too: refactored helpers import shared infra
  # from .devforge/lib/_shared/ (e.g. _audit/_cli.py does `from _shared._consume
  # import ...`), so a command-only delivery that omitted it would leave the
  # target unable to import. _shared/ is framework-owned (no user state) — clean
  # replace. (Refreshes shared code other commands use; for strict cross-command
  # version consistency, run a full update instead.)
  if [ -d "$TEMPLATE_DIR/src/devforge/lib/_shared" ]; then
    rm -rf "$TARGET_DIR/.devforge/lib/_shared"
    cp -R "$TEMPLATE_DIR/src/devforge/lib/_shared" "$TARGET_DIR/.devforge/lib/_shared"
    rm -rf "$TARGET_DIR/.devforge/lib/_shared/__pycache__"
    echo "  shared deps: .devforge/lib/_shared/"
    helper_found=true
  fi
  # Ship _implement/ always: _artifact/_cli.py imports resolve_workspace from
  # _implement._workspace at import time (before main()'s catch-all), so a
  # --only delivery to an install missing _implement/ would hard-crash the
  # launcher with an ImportError rather than failing gracefully. Mirror the
  # _shared/ always-copy pattern — resolve_workspace is not moved (heavier
  # change) so the dependency must be satisfied instead.
  if [ -d "$TEMPLATE_DIR/src/devforge/lib/_implement" ]; then
    rm -rf "$TARGET_DIR/.devforge/lib/_implement"
    cp -R "$TEMPLATE_DIR/src/devforge/lib/_implement" "$TARGET_DIR/.devforge/lib/_implement"
    rm -rf "$TARGET_DIR/.devforge/lib/_implement/__pycache__"
    echo "  implement deps: .devforge/lib/_implement/"
    helper_found=true
  fi
  # Ship artifact_helper always: every edited command (Phases 2-9 of plan 37)
  # calls .devforge/lib/artifact_helper commit-artifacts. A surgical --only
  # delivery of ANY command that uses the verb requires artifact_helper to be
  # present — mirror the _shared/ always-copy pattern.
  if [ -d "$TEMPLATE_DIR/src/devforge/lib/_artifact" ]; then
    rm -rf "$TARGET_DIR/.devforge/lib/_artifact"
    cp -R "$TEMPLATE_DIR/src/devforge/lib/_artifact" "$TARGET_DIR/.devforge/lib/_artifact"
    rm -rf "$TARGET_DIR/.devforge/lib/_artifact/__pycache__"
    echo "  artifact helper: .devforge/lib/_artifact/"
    helper_found=true
  fi
  for _artifact_launcher in "artifact_helper" "artifact_helper.py"; do
    if [ -f "$TEMPLATE_DIR/src/devforge/lib/$_artifact_launcher" ]; then
      cp "$TEMPLATE_DIR/src/devforge/lib/$_artifact_launcher" "$TARGET_DIR/.devforge/lib/$_artifact_launcher"
      echo "  artifact launcher: .devforge/lib/$_artifact_launcher"
      helper_found=true
    fi
  done
  if [ -f "$TARGET_DIR/.devforge/lib/artifact_helper" ]; then
    chmod +x "$TARGET_DIR/.devforge/lib/artifact_helper"
  fi
  # Ship _design/ always (plan 53): it is a cross-cutting runtime dependency of
  # /breakdown (design_helper check-design-source + validate-binding),
  # /review's design-auditor (design_helper compare, plus the JS collectors at
  # .devforge/lib/_design/js/{built,intent}_reader.js run via evaluate_script —
  # cp -R below carries js/ recursively), and /implement's verify-design-tokens
  # forcing function (imports _design.extract_spacing_scale). A surgical --only
  # delivery of any of those commands would otherwise miss it — mirror the
  # _shared/_implement/_artifact always-copy pattern.
  if [ -d "$TEMPLATE_DIR/src/devforge/lib/_design" ]; then
    rm -rf "$TARGET_DIR/.devforge/lib/_design"
    cp -R "$TEMPLATE_DIR/src/devforge/lib/_design" "$TARGET_DIR/.devforge/lib/_design"
    rm -rf "$TARGET_DIR/.devforge/lib/_design/__pycache__"
    echo "  design helper: .devforge/lib/_design/"
    helper_found=true
  fi
  for _design_launcher in "design_helper" "design_helper.py"; do
    if [ -f "$TEMPLATE_DIR/src/devforge/lib/$_design_launcher" ]; then
      cp "$TEMPLATE_DIR/src/devforge/lib/$_design_launcher" "$TARGET_DIR/.devforge/lib/$_design_launcher"
      echo "  design launcher: .devforge/lib/$_design_launcher"
      helper_found=true
    fi
  done
  if [ -f "$TARGET_DIR/.devforge/lib/design_helper" ]; then
    chmod +x "$TARGET_DIR/.devforge/lib/design_helper"
  fi
  for _launcher in "${cmd_u}_helper" "${cmd_u}_helper.py"; do
    if [ -f "$TEMPLATE_DIR/src/devforge/lib/$_launcher" ]; then
      cp "$TEMPLATE_DIR/src/devforge/lib/$_launcher" "$TARGET_DIR/.devforge/lib/$_launcher"
      echo "  helper launcher: .devforge/lib/$_launcher"
      helper_found=true
    fi
  done
  # cp drops the executable bit without -p; restore it on the extension-less
  # launcher (the entry point invoked as .devforge/lib/<cmd>_helper).
  if [ -f "$TARGET_DIR/.devforge/lib/${cmd_u}_helper" ]; then
    chmod +x "$TARGET_DIR/.devforge/lib/${cmd_u}_helper"
  fi
  if [ "$helper_found" = false ]; then
    echo "  (no helper subpackage/launcher for '$ONLY_CMD' — command-only delivery)"
  fi

  echo ""
  echo "Done. Surgically delivered '$ONLY_CMD' to $TARGET_DIR (nothing else touched)."
  exit 0
fi

echo "Installing AIDevTeamForge into: $TARGET_DIR"

# ── Copy .devforge/ scaffolding + runtime helpers ────────────────────────
# Must run BEFORE generate.sh: the emitter writes command reference files to
# .devforge/command-refs/<cmd>/ (plan 63 — relocated out of .claude/commands/
# to avoid phantom-command menu pollution). If we copied the scaffolding
# AFTER the emitter ran, cp -R would nest src/devforge into an
# already-existing .devforge/ → wrong layout .devforge/devforge/*. This
# ordering is now genuinely load-bearing (not just a directory-nesting
# precaution) — the emitter really does write under .devforge/ on every run.
#
# The `src/devforge/.` + trailing `/` syntax copies CONTENTS (not the
# folder itself) so this is idempotent regardless of whether .devforge/
# pre-exists. cp -R preserves the executable bit on the launcher scripts
# in src/devforge/lib/ (e.g. init_helper, configure_helper, generate_docs_helper).
#
# Runtime helpers ride along: everything under src/devforge/lib/ lands at
# .devforge/lib/ on the target via this single cp -R.
# Guard against stray user-state files in the framework source tree.
# init.yaml / configure.yaml are USER STATE generated by /init-forge +
# /configure on the target, NOT framework-shipped templates. If they
# exist in src/devforge/ they are leftover artifacts from running the
# helpers from inside the framework repo (DEVFORGE_DIR unset). Copying
# them into the target overwrites the target's real state and silently
# wipes wrapper-mode + packages_detected.
for _stray in init.yaml configure.yaml configure.yaml.lock constitute.json constitute.json.lock .preflight-stamp .generate-docs-trace.log; do
    if [ -f "$TEMPLATE_DIR/src/devforge/$_stray" ]; then
        echo "error: stray user-state file in framework source: src/devforge/$_stray" >&2
        echo "  This file is generated by helpers; it must NOT live in the source tree." >&2
        echo "  install.sh would copy it over the target's real state on this install." >&2
        echo "  Fix: rm '$TEMPLATE_DIR/src/devforge/$_stray' and re-run install." >&2
        exit 1
    fi
done

mkdir -p "$TARGET_DIR/.devforge"
cp -R "$TEMPLATE_DIR/src/devforge/." "$TARGET_DIR/.devforge/"

# ── .gitignore: ensure .devforge/ runtime-state rules present ──────────────
# install.sh does NOT run the manifest mergeFiles machinery (that lives only in
# update.sh); apply the dedicated consumer gitignore template inline so a FRESH
# install is clean from cycle 1 (plan 49 Phase 1 / OQ-5). union_lines semantics:
# add each missing line, never remove a project's own. Install-repo-only.
_gi_src="$TEMPLATE_DIR/src/files/devforge.gitignore"
_gi_tgt="$TARGET_DIR/.gitignore"
if [ -f "$_gi_src" ]; then
  touch "$_gi_tgt"
  while IFS= read -r _gi_line; do
    [ -z "$_gi_line" ] && continue
    grep -qxF "$_gi_line" "$_gi_tgt" 2>/dev/null || printf '%s\n' "$_gi_line" >> "$_gi_tgt"
  done < "$_gi_src"
  echo "  gitignore: .devforge/ runtime-state rules ensured"
fi
# Re-install onto an already-forge'd target may carry tracked ephemeral files +
# the dead ignore line; migrate them (shared with update.sh, fail-soft no-op on
# a genuinely fresh install where none are tracked). Runs AFTER the union above.
forge_migrate_devforge_state "$TARGET_DIR"

# ── Place constitution.md at project root (presence-guarded) ──────────────
# Brownfield safety: if the target already has a constitution.md, leave it
# alone. The wizard's Phase 3 §5.7 substitutes header placeholders only,
# and /constitute (later) fills body sections — both operate on whatever
# file is present.
if [ ! -f "$TARGET_DIR/constitution.md" ]; then
  cp "$TEMPLATE_DIR/src/constitution.md" "$TARGET_DIR/constitution.md"
else
  echo "  existing constitution.md detected — leaving as-is"
  # Constitution drift check (plan 44): the presence guard above skips placing a
  # fresh constitution, so the existing one may be stale relative to the template.
  # WARN-ONLY + fail-soft; never blocks the install.
  forge_check_constitution_drift "$TARGET_DIR" "$TEMPLATE_DIR"
fi

# ── Place docs/ stubs (per-file presence-guarded) ─────────────────────────
# Only two files are scaffolded: docs/overview.md and docs/architecture.md.
# Everything under docs/ (features/, api/, guides/) springs into existence
# when tech-writer creates its first file there — no empty dirs with
# .gitkeep. Per-file guard: if the user has overview.md but not
# architecture.md, only the missing one is copied.
mkdir -p "$TARGET_DIR/docs"
for f in overview.md architecture.md; do
  if [ ! -f "$TARGET_DIR/docs/$f" ]; then
    cp "$TEMPLATE_DIR/src/docs/$f" "$TARGET_DIR/docs/$f"
  else
    echo "  existing docs/$f detected — leaving as-is"
  fi
done

# ── Place CLAUDE.md primer at project root ────────────────────────────────
# The wizard later substitutes the {{UPPERCASE}} placeholders inside it
# with project-specific answers (PROJECT_NAME, FRAMEWORK, etc.).
cp "$TEMPLATE_DIR/src/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"

# ── Build Claude files via the generator ──────────────────────────────────
# install.sh is intentionally dumb: it scaffolds shared dirs and delegates
# Claude file generation (commands, agents) to scripts/generate.sh.
"$TEMPLATE_DIR/scripts/generate.sh" "$TARGET_DIR"

# ── Clean up pre-move flat command layout (plan 63 namespace move) ─────────
# On a re-install into an existing consumer, an old flat
# .claude/commands/<name>.md (+ .claude/commands/<name>/references/) from
# before the devforge/ namespace move would otherwise survive alongside the
# command generate.sh + the emitter just wrote to
# .claude/commands/devforge/<name>.md — leaving BOTH a stale and a live copy,
# so a typed /<name> would resolve to the stale one. install.sh has no
# general-purpose command pruner (that is update.sh's FIX-B); this targets
# only the specific canonical-named paths the namespace move makes stale.
# Fail-soft: absent paths / a failed --list are a no-op. Reuses PY_CMD
# resolved by the module-level Python 3 preflight above (guaranteed set — that
# preflight aborts install.sh otherwise), instead of re-detecting Python here.
if [ -d "$TARGET_DIR/.claude/commands" ]; then
  _canon_cmds="$($PY_CMD "$TEMPLATE_DIR/scripts/emitters/claude.py" --list 2>/dev/null || true)"
  if [ -n "$_canon_cmds" ]; then
    echo "$_canon_cmds" | while IFS= read -r _cname; do
      [ -z "$_cname" ] && continue
      if [ -f "$TARGET_DIR/.claude/commands/$_cname.md" ]; then
        rm -f "$TARGET_DIR/.claude/commands/$_cname.md"
        echo "  removed stale: .claude/commands/$_cname.md"
      fi
      if [ -d "$TARGET_DIR/.claude/commands/$_cname" ]; then
        rm -rf "$TARGET_DIR/.claude/commands/$_cname"
        echo "  removed stale: .claude/commands/$_cname/"
      fi
    done
  fi
fi

# ── Snapshot template output to .devforge/template/ ───────────────────────
# Stores raw (un-substituted) generated files so update.sh can three-way
# merge on the very first update — fixes the first-update gap where the old
# scattered .baseline/ approach skipped merging until the second update.
mkdir -p "$TARGET_DIR/.devforge/template/.claude/agents"
cp -R "$TARGET_DIR/.claude/agents/." "$TARGET_DIR/.devforge/template/.claude/agents/"
cp "$TARGET_DIR/CLAUDE.md" "$TARGET_DIR/.devforge/template/CLAUDE.md"

# ── Copy Claude config files ──────────────────────────────────────────────
#   .mcp.json             — MCP servers (project-scope)
#   .claude/settings.json — hooks, permissions, plugins
#   .claude/hooks/        — CBM-first enforcement hook scripts (F.11)
cp "$TEMPLATE_DIR/src/mcp.json" "$TARGET_DIR/.mcp.json"
mkdir -p "$TARGET_DIR/.claude"
cp "$TEMPLATE_DIR/src/settings.template.json" "$TARGET_DIR/.claude/settings.json"
mkdir -p "$TARGET_DIR/.claude/hooks"
cp -R "$TEMPLATE_DIR/src/hooks/." "$TARGET_DIR/.claude/hooks/"
chmod +x "$TARGET_DIR/.claude/hooks/"*

# ── Copy pre-commit hook templates ───────────────────────────────────────────
#   Shipped to .devforge/templates/git-hooks/ so the user can opt in via the
#   /constitute wizard.  NOT auto-installed into .git/hooks/ — requires
#   explicit user opt-in.
mkdir -p "$TARGET_DIR/.devforge/templates/git-hooks"
cp -R "$TEMPLATE_DIR/src/git-hooks/." "$TARGET_DIR/.devforge/templates/git-hooks/"
chmod +x "$TARGET_DIR/.devforge/templates/git-hooks/"*.sh

# ── Stamp .claude/template-version (D3, plan 72) ───────────────────────────
# update.sh reads this marker to report the installed template version and,
# via its repair-mode guard, install completeness. Without it a fresh
# install reports "Target version: (unknown)" to update.sh — benign for the
# equal-version bail, but it silently suppresses the changelog-excerpt block
# gated on a known version (update.sh's changelog-excerpt block). Read via $PY_CMD (already
# preflight-gated above), not jq — install.sh has no jq dependency and this
# one-line read is not worth adding one. Fail-soft: install.sh has no
# `set -e`, so a failed/empty read must not be left to silently do nothing —
# warn explicitly and skip the stamp; a successful install must never be
# turned into a failure over the marker.
_tv="$($PY_CMD -c 'import json, sys; print(json.load(open(sys.argv[1]))["version"])' "$TEMPLATE_DIR/src/manifest.json" 2>/dev/null)"
if [ -n "$_tv" ]; then
  printf '%s\n' "$_tv" > "$TARGET_DIR/.claude/template-version"
  echo "  version marker: .claude/template-version → $_tv"
else
  echo "  warning: could not read template version from src/manifest.json — .claude/template-version not written"
fi

echo ""
echo "Done. AIDevTeamForge installed."
echo "CBM sync: SessionStart hook (cbm-sync-session-start) compares .devforge/cbm-last-indexed-sha to parent HEAD on every session boot and prompts Claude to call detect_changes / index_repository when stale."
echo "Next — open the project in Claude Code and run, in order:"
echo "  /devforge:init-forge      — bootstrap structural fields"
echo "  /devforge:generate-docs   — deep codebase scan"
echo "  /devforge:configure       — populate config + substitute templates"
echo "  /devforge:constitute      — synthesize constitution.md"
