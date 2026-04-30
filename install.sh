#!/bin/bash
# install.sh — Install AIDevTeamForge template into a target project directory.
#
# Responsibility: copy files and create directory structure. Nothing more.
# All project detection and configuration happens in /setup-wizard (run later,
# inside the target, by Claude Code). The wizard handles all mode-specific
# concerns — including wrapper-mode detection and any user-confirmed
# `.gitignore` updates for an inner project folder. install.sh stays dumb.
#
# Usage:
#   install.sh <target-directory>

# ── Resolve the template repo path (where this script lives) ───────────────
TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Parse arguments ────────────────────────────────────────────────────────
TARGET_DIR=""

while [ $# -gt 0 ]; do
  case "$1" in
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

# ── Copy .devforge/ scaffolding + runtime helpers ────────────────────────
# Must run BEFORE generate.sh: emitters may create subdirectories under
# .devforge/ (e.g. .devforge/commands/<cmd>/references/ for folder-based
# commands). If we copied the scaffolding AFTER the emitter ran, cp -R
# would nest src/devforge into an already-existing .devforge/ → wrong
# layout .devforge/devforge/*.
#
# The `src/devforge/.` + trailing `/` syntax copies CONTENTS (not the
# folder itself) so this is idempotent regardless of whether .devforge/
# pre-exists. cp -R preserves the executable bit on the launcher scripts
# in src/devforge/lib/ (detect_report, wizard_render, onboard_helper).
#
# Runtime helpers ride along: src/devforge/lib/{detect_report,wizard_render,
# onboard_helper}{,.py} are the wizard-time and onboard-time helpers; they
# land at .devforge/lib/ on the target via this single cp -R.
mkdir -p "$TARGET_DIR/.devforge"
cp -R "$TEMPLATE_DIR/src/devforge/." "$TARGET_DIR/.devforge/"

# ── Place constitution.md at project root (presence-guarded) ──────────────
# Brownfield safety: if the target already has a constitution.md, leave it
# alone. The wizard's Phase 3 §5.7 substitutes header placeholders only,
# and /constitute (later) fills body sections — both operate on whatever
# file is present.
if [ ! -f "$TARGET_DIR/constitution.md" ]; then
  cp "$TEMPLATE_DIR/src/constitution.md" "$TARGET_DIR/constitution.md"
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
cp "$TEMPLATE_DIR/src/mcp.json" "$TARGET_DIR/.mcp.json"
mkdir -p "$TARGET_DIR/.claude"
cp "$TEMPLATE_DIR/src/settings.template.json" "$TARGET_DIR/.claude/settings.json"

echo ""
echo "Done. AIDevTeamForge installed."
echo "Next — open the project and run /init-forge in Claude Code."
