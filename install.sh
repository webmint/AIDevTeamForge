#!/bin/bash
# Install Claude Hybrid Template into a target project directory
#
# Usage:
#   install.sh <target-directory>
#   install.sh --wrapper <target-directory> <inner-project-folder>

TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"

# Parse arguments
WRAPPER_MODE=false
TARGET_DIR=""
INNER_FOLDER=""

while [ $# -gt 0 ]; do
  case "$1" in
    --wrapper) WRAPPER_MODE=true; shift ;;
    -*) echo "Unknown flag: $1"; exit 1 ;;
    *)
      if [ -z "$TARGET_DIR" ]; then
        TARGET_DIR="$1"
      elif [ -z "$INNER_FOLDER" ]; then
        INNER_FOLDER="$1"
      fi
      shift
      ;;
  esac
done

if [ -z "$TARGET_DIR" ] || [ "$TARGET_DIR" = "." ]; then
  echo "Usage: install.sh [--wrapper] <target-directory> [inner-project-folder]"
  echo ""
  echo "Examples:"
  echo "  ./install.sh ~/Projects/my-app"
  echo "  ./install.sh --wrapper ~/Projects/my-workspace client-project"
  exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
  echo "Directory '$TARGET_DIR' does not exist. Create it first."
  exit 1
fi

# Wrapper mode validation
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
  if [ ! -d "$TARGET_DIR/$INNER_FOLDER/.git" ]; then
    echo "Warning: '$INNER_FOLDER' does not appear to be a git repository (no .git/ found)."
    echo "Continuing anyway..."
  fi
fi

echo "Installing Claude Hybrid Template into: $TARGET_DIR"

cp -r "$TEMPLATE_DIR/.claude" "$TARGET_DIR/"
cp -r "$TEMPLATE_DIR/specs" "$TARGET_DIR/"
cp -r "$TEMPLATE_DIR/scripts" "$TARGET_DIR/"
cp "$TEMPLATE_DIR/.mcp.json" "$TARGET_DIR/"

# Write template version for future updates
TEMPLATE_VERSION="$(cat "$TEMPLATE_DIR/.claude/template-version" 2>/dev/null || echo "1.0.0")"
echo "$TEMPLATE_VERSION" > "$TARGET_DIR/.claude/template-version"

# Wrapper mode: add inner folder to .gitignore
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
  echo "Done. Template version $TEMPLATE_VERSION installed (wrapper mode)."
  echo "Source root: $INNER_FOLDER/"
  echo "Open the project in Claude Code and run /setup-wizard"
else
  echo ""
  echo "Done. Template version $TEMPLATE_VERSION installed."
  echo "Open the project in Claude Code and run /setup-wizard"
fi
