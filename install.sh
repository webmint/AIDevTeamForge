#!/bin/bash
# install.sh — Install AIDevTeamForge template into a target project directory.
#
# Responsibility: copy files and create directory structure. Nothing more.
# All project detection and configuration happens in /setup-wizard (run later,
# inside the target, by an LLM CLI such as Claude Code or Codex CLI).
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

echo "Installing AIDevTeamForge into: $TARGET_DIR"

# ── Build runtime-specific files via the generator ─────────────────────────
# install.sh is intentionally dumb: it scaffolds shared dirs and delegates
# all runtime-specific work (Claude, Codex, later Cursor/Gemini) to the
# generator. Each runtime has its own emitter in scripts/emitters/.
# Adding a new runtime = adding one emitter file + registering it in
# scripts/generate.sh. install.sh never needs to change.
"$TEMPLATE_DIR/scripts/generate.sh" "$TARGET_DIR"

# ── Copy cross-runtime scaffolding (.devforge/) ──────────────────────────
# Shared across all runtimes: project config, memory, storage rules.
# Session-state and wip markers are created at runtime by commands.
cp -r "$TEMPLATE_DIR/src/devforge" "$TARGET_DIR/.devforge"

# ── Copy runtime config files (per-runtime, not shared) ─────────────────
# Each runtime gets whatever config files it natively uses — no forced
# symmetry. All files contain {{PLACEHOLDERS}} that wizard STEP 5 populates.
#
# Claude:
#   .mcp.json           — MCP servers (project-scope)
#   .claude/settings.json — hooks, permissions, plugins
# Codex:
#   .codex/config.toml  — model, sandbox, approval_policy, MCP servers
cp "$TEMPLATE_DIR/src/files/mcp.json" "$TARGET_DIR/.mcp.json"
mkdir -p "$TARGET_DIR/.claude"
cp "$TEMPLATE_DIR/src/files/settings.template.json" "$TARGET_DIR/.claude/settings.json"
mkdir -p "$TARGET_DIR/.codex"
cp "$TEMPLATE_DIR/src/files/config.toml" "$TARGET_DIR/.codex/config.toml"

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
  echo "Open the project in Claude Code or Codex CLI and run /setup-wizard"
else
  echo ""
  echo "Done. AIDevTeamForge installed."
  echo "Open the project in Claude Code or Codex CLI and run /setup-wizard"
fi
