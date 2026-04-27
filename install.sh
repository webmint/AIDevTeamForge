#!/bin/bash
# install.sh — Install AIDevTeamForge template into a target project directory.
#
# Responsibility: copy files and create directory structure. Nothing more.
# All project detection and configuration happens in /setup-wizard (run later,
# inside the target, by Claude Code).
#
# Usage:
#   install.sh <target-directory>
#   install.sh --wrapper <target-directory> <inner-project-folder>
#
# The wrapper mode is for cases where the client's source code lives in an
# inner git repo and the template artifacts should live in an outer workspace
# that does not touch the inner repo's files.

# ── Resolve the template repo path (where this script lives) ───────────────
TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Parse arguments ────────────────────────────────────────────────────────
WRAPPER_MODE=false
TARGET_DIR=""
INNER_FOLDER=""

while [ $# -gt 0 ]; do
  case "$1" in
    --wrapper)
      WRAPPER_MODE=true
      shift
      ;;
    -*)
      echo "Unknown flag: $1"
      exit 1
      ;;
    *)
      # First positional = target dir, second (wrapper only) = inner folder.
      if [ -z "$TARGET_DIR" ]; then
        TARGET_DIR="$1"
      elif [ -z "$INNER_FOLDER" ]; then
        INNER_FOLDER="$1"
      fi
      shift
      ;;
  esac
done

# ── Validate target directory ──────────────────────────────────────────────
# Refuse to install into the current directory as a safety guard — users
# should pass an explicit target path.
if [ -z "$TARGET_DIR" ] || [ "$TARGET_DIR" = "." ]; then
  echo "Usage: install.sh [--wrapper] <target-directory> [inner-project-folder]"
  echo ""
  echo "Examples:"
  echo "  ./install.sh ~/Projects/my-app"
  echo "  ./install.sh --wrapper ~/Projects/my-workspace client-project"
  exit 1
fi

# Target must exist — users create it first (empty dir is fine).
if [ ! -d "$TARGET_DIR" ]; then
  echo "Directory '$TARGET_DIR' does not exist. Create it first."
  exit 1
fi

# ── Wrapper mode validation ────────────────────────────────────────────────
# Wrapper mode requires an inner project folder name. The inner folder must
# already exist inside the target; it's usually a separate git repo that the
# wrapper will never touch except via .gitignore.
if [ "$WRAPPER_MODE" = true ]; then
  if [ -z "$INNER_FOLDER" ]; then
    echo "Wrapper mode requires an inner project folder name."
    echo "Usage: install.sh --wrapper <target-directory> <inner-project-folder>"
    exit 1
  fi
  if [ ! -d "$TARGET_DIR/$INNER_FOLDER" ]; then
    echo "Inner project folder '$TARGET_DIR/$INNER_FOLDER' does not exist."
    exit 1
  fi
  # Informational only — inner project without .git is unusual but allowed.
  if [ ! -d "$TARGET_DIR/$INNER_FOLDER/.git" ]; then
    echo "Warning: '$INNER_FOLDER' does not appear to be a git repository (no .git/ found)."
    echo "Continuing anyway..."
  fi
fi

# ── Python 3 preflight ─────────────────────────────────────────────────────
# Install-time generators (scripts/generate.sh → generate-agents.py /
# generate-corellm.py / emitters) and the wizard-time Detection Report
# composer (scripts/lib/detect_report.py) all require Python 3. Surface the
# dependency now rather than letting it fail mid-install.
if command -v python3 >/dev/null 2>&1; then
  : # python3 ok
elif command -v py >/dev/null 2>&1; then
  : # Windows Python launcher routes to 3.x
elif command -v python >/dev/null 2>&1 && [ "$(python -c 'import sys; print(sys.version_info[0])' 2>/dev/null)" = "3" ]; then
  : # bare python is 3.x
else
  echo "AIDevTeamForge requires Python 3 on the target machine." >&2
  echo "Install Python 3.8+ (https://www.python.org/downloads/) and re-run." >&2
  exit 1
fi

echo "Installing AIDevTeamForge into: $TARGET_DIR"

# ── Copy cross-runtime scaffolding (.devforge/) ──────────────────────────
# Must run BEFORE generate.sh: emitters may create subdirectories under
# .devforge/ (e.g. .devforge/commands/<cmd>/references/ for folder-based
# commands). If we copied the scaffolding AFTER the emitter ran, cp -r
# would nest src/devforge into an already-existing .devforge/ → the wrong
# layout .devforge/devforge/*.
#
# The `src/devforge/.` + trailing `/` syntax copies CONTENTS (not the
# folder itself) so this is idempotent regardless of whether .devforge/
# pre-exists.
#
# .devforge/ ownership: install.sh creates eagerly because the cp -R below
# requires the directory to exist. The wizard-time composer
# (scripts/lib/detect_report.py) also calls mkdir(exist_ok=True) defensively
# so standalone composer use (without install.sh) and update flows still
# work. Belt-and-suspenders by design — see PATH-B-IMPLEMENTATION.md
# Step 3.3 decision (option c).
mkdir -p "$TARGET_DIR/.devforge"
cp -R "$TEMPLATE_DIR/src/devforge/." "$TARGET_DIR/.devforge/"

# ── Copy setup-wizard + onboard runtime helpers ────────────────────────────
# scripts/lib/detect_report{,.py} compose the Phase 1 Detection Report at
# wizard-time. The launcher (no extension) picks a Python 3 interpreter; the
# .py module is the composer. Both must land on the target — generators
# elsewhere in scripts/ stay template-internal.
#
# scripts/lib/onboard_helper{,.py} register doc artifacts and atomically
# compose docs/ at onboard-time. Same launcher-pattern. The helper enforces
# 7 validation gates (per-package coverage, per-concern decomposition,
# block/ref count equality, boilerplate-overview, principal-type presence,
# type dedup, cross-link + sigil hygiene) at compose time.
mkdir -p "$TARGET_DIR/scripts/lib"
cp "$TEMPLATE_DIR/scripts/lib/detect_report" "$TARGET_DIR/scripts/lib/detect_report"
cp "$TEMPLATE_DIR/scripts/lib/detect_report.py" "$TARGET_DIR/scripts/lib/detect_report.py"
chmod +x "$TARGET_DIR/scripts/lib/detect_report"
cp "$TEMPLATE_DIR/scripts/lib/onboard_helper" "$TARGET_DIR/scripts/lib/onboard_helper"
cp "$TEMPLATE_DIR/scripts/lib/onboard_helper.py" "$TARGET_DIR/scripts/lib/onboard_helper.py"
chmod +x "$TARGET_DIR/scripts/lib/onboard_helper"

# ── Place constitution.md at project root (presence-guarded) ──────────────
# Brownfield safety: if the target already has a constitution.md, leave it
# alone. The wizard's Phase 3 §5.7 substitutes header placeholders only,
# and /constitute (later) fills body sections — both operate on whatever
# file is present.
if [ ! -f "$TARGET_DIR/constitution.md" ]; then
  cp "$TEMPLATE_DIR/src/files/constitution.md" "$TARGET_DIR/constitution.md"
else
  echo "  existing constitution.md detected — leaving as-is"
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
    cp "$TEMPLATE_DIR/src/files/docs/$f" "$TARGET_DIR/docs/$f"
  else
    echo "  existing docs/$f detected — leaving as-is"
  fi
done

# ── Place CLAUDE.md primer at project root ────────────────────────────────
# The wizard later substitutes the {{UPPERCASE}} placeholders inside it
# with project-specific answers (PROJECT_NAME, FRAMEWORK, etc.).
cp "$TEMPLATE_DIR/src/files/coreLLM/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"

# ── Build runtime-specific files via the generator ─────────────────────────
# install.sh is intentionally dumb: it scaffolds shared dirs and delegates
# all runtime-specific work (Claude, Codex, later Cursor/Gemini) to the
# generator. Each runtime has its own emitter in scripts/emitters/.
# Adding a new runtime = adding one emitter file + registering it in
# scripts/generate.sh. install.sh never needs to change.
"$TEMPLATE_DIR/scripts/generate.sh" "$TARGET_DIR"

# ── Copy runtime config files (per-runtime, not shared) ─────────────────
# Each runtime gets whatever config files it natively uses — no forced
# symmetry.
#
# Claude:
#   .mcp.json             — MCP servers (project-scope)
#   .claude/settings.json — hooks, permissions, plugins
# Codex:
#   .codex/config.toml    — model, sandbox, approval_policy, MCP servers
cp "$TEMPLATE_DIR/src/files/mcp.json" "$TARGET_DIR/.mcp.json"
mkdir -p "$TARGET_DIR/.claude"
cp "$TEMPLATE_DIR/src/files/settings.template.json" "$TARGET_DIR/.claude/settings.json"

# # ── Copy project-level scaffolding ─────────────────────────────────────────
# # These directories belong at the target root (not under .claude/).
# # They're shared across all runtimes and all workflows.
# cp -r "$TEMPLATE_DIR/specs" "$TARGET_DIR/"         # feature specifications
# cp -r "$TEMPLATE_DIR/bugs" "$TARGET_DIR/"          # bug reports for /fix
# cp -r "$TEMPLATE_DIR/research" "$TARGET_DIR/"      # /research output
# cp -r "$TEMPLATE_DIR/scripts" "$TARGET_DIR/"       # helper shell scripts
# cp "$TEMPLATE_DIR/.mcp.json" "$TARGET_DIR/"        # MCP server config
#
# # ── Record template version in the target ──────────────────────────────────
# # update.sh uses this to decide what diffs to apply on upgrade. The source of
# # truth is the VERSION file at the template repo root.
# TEMPLATE_VERSION="$(cat "$TEMPLATE_DIR/VERSION" 2>/dev/null || echo "1.0.0")"
# echo "$TEMPLATE_VERSION" > "$TARGET_DIR/.claude/template-version"

# ── Wrapper mode finalization ──────────────────────────────────────────────
# In wrapper mode the outer workspace is the "target". The inner folder is a
# separate git repo whose files we must never track. Add it to the wrapper's
# .gitignore if not already present.
if [ "$WRAPPER_MODE" = true ]; then
  GITIGNORE="$TARGET_DIR/.gitignore"
  ENTRY="$INNER_FOLDER/"
  if [ -f "$GITIGNORE" ] && grep -qxF "$ENTRY" "$GITIGNORE" 2>/dev/null; then
    echo "Inner folder '$INNER_FOLDER/' already in .gitignore"
  else
    echo "" >> "$GITIGNORE"
    echo "# Inner project (separate git repo)" >> "$GITIGNORE"
    echo "$ENTRY" >> "$GITIGNORE"
    echo "Added '$INNER_FOLDER/' to .gitignore"
  fi
  echo ""
  echo "Done. AIDevTeamForge installed (wrapper mode)."
  echo "Source root: $INNER_FOLDER/"
  echo "Next — open the project and run /setup-wizard in Claude Code."
else
  echo ""
  echo "Done. AIDevTeamForge installed."
  echo "Next — open the project and run /setup-wizard in Claude Code."
fi
