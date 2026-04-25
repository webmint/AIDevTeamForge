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
# Comma-separated runtime list. Empty = install all registered runtimes
# (whatever generate.sh defaults to). Populated from --runtime flag.
RUNTIMES_CSV=""

# Canonical list of runtimes install.sh knows how to gate files for.
# Must stay in sync with scripts/generate.sh's RUNTIMES default.
VALID_RUNTIMES="claude codex"

while [ $# -gt 0 ]; do
  case "$1" in
    --wrapper)
      WRAPPER_MODE=true
      shift
      ;;
    --runtime)
      RUNTIMES_CSV="$2"
      shift 2
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

# Validate --runtime values. Empty means "all" — no validation needed.
if [ -n "$RUNTIMES_CSV" ]; then
  # Split on comma, check each against VALID_RUNTIMES.
  OLD_IFS="$IFS"; IFS=','
  for r in $RUNTIMES_CSV; do
    case " $VALID_RUNTIMES " in
      *" $r "*) ;;
      *) echo "Unknown runtime: '$r'. Valid: $VALID_RUNTIMES" >&2; exit 1 ;;
    esac
  done
  IFS="$OLD_IFS"
fi

# has_runtime <name> — returns 0 if the runtime is selected (or no filter set).
has_runtime() {
  [ -z "$RUNTIMES_CSV" ] && return 0
  case ",$RUNTIMES_CSV," in *",$1,"*) return 0 ;; esac
  return 1
}

# ── Validate target directory ──────────────────────────────────────────────
# Refuse to install into the current directory as a safety guard — users
# should pass an explicit target path.
if [ -z "$TARGET_DIR" ] || [ "$TARGET_DIR" = "." ]; then
  echo "Usage: install.sh [--wrapper] [--runtime <csv>] <target-directory> [inner-project-folder]"
  echo ""
  echo "  --runtime <csv>  Comma-separated runtime list. Omit = all ($VALID_RUNTIMES)."
  echo "                   Valid values: $VALID_RUNTIMES"
  echo ""
  echo "Examples:"
  echo "  ./install.sh ~/Projects/my-app"
  echo "  ./install.sh --runtime claude ~/Projects/my-app"
  echo "  ./install.sh --runtime claude,codex ~/Projects/my-app"
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
mkdir -p "$TARGET_DIR/.devforge"
cp -R "$TEMPLATE_DIR/src/devforge/." "$TARGET_DIR/.devforge/"

# ── Copy setup-wizard runtime helpers ───────────────────────────────────────
# scripts/lib/detect_report{,.py} compose the Phase 1 Detection Report at
# wizard-time. The launcher (no extension) picks a Python 3 interpreter; the
# .py module is the composer. Both must land on the target — generators
# elsewhere in scripts/ stay template-internal.
mkdir -p "$TARGET_DIR/scripts/lib"
cp "$TEMPLATE_DIR/scripts/lib/detect_report" "$TARGET_DIR/scripts/lib/detect_report"
cp "$TEMPLATE_DIR/scripts/lib/detect_report.py" "$TARGET_DIR/scripts/lib/detect_report.py"
chmod +x "$TARGET_DIR/scripts/lib/detect_report"

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

# ── Build runtime-specific files via the generator ─────────────────────────
# install.sh is intentionally dumb: it scaffolds shared dirs and delegates
# all runtime-specific work (Claude, Codex, later Cursor/Gemini) to the
# generator. Each runtime has its own emitter in scripts/emitters/.
# Adding a new runtime = adding one emitter file + registering it in
# scripts/generate.sh. install.sh never needs to change.
#
# Forward runtime selection: if --runtime was passed, generate.sh reads
# the RUNTIMES env var (space-separated) to filter. Empty = all.
if [ -n "$RUNTIMES_CSV" ]; then
  RUNTIMES="$(echo "$RUNTIMES_CSV" | tr ',' ' ')" "$TEMPLATE_DIR/scripts/generate.sh" "$TARGET_DIR"
else
  "$TEMPLATE_DIR/scripts/generate.sh" "$TARGET_DIR"
fi

# ── Copy runtime config files (per-runtime, not shared) ─────────────────
# Each runtime gets whatever config files it natively uses — no forced
# symmetry. Only the runtimes selected via --runtime (or all by default)
# get their config files placed.
#
# Claude:
#   .mcp.json             — MCP servers (project-scope)
#   .claude/settings.json — hooks, permissions, plugins
# Codex:
#   .codex/config.toml    — model, sandbox, approval_policy, MCP servers
if has_runtime claude; then
  cp "$TEMPLATE_DIR/src/files/mcp.json" "$TARGET_DIR/.mcp.json"
  mkdir -p "$TARGET_DIR/.claude"
  cp "$TEMPLATE_DIR/src/files/settings.template.json" "$TARGET_DIR/.claude/settings.json"
fi
if has_runtime codex; then
  mkdir -p "$TARGET_DIR/.codex"
  cp "$TEMPLATE_DIR/src/files/config.toml" "$TARGET_DIR/.codex/config.toml"
fi

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
# ── Closing message: per-runtime launch instructions ─────────────────────
# Each runtime has its own invocation syntax:
#   Claude Code: slash command /setup-wizard
#   Codex CLI  : skills are invoked by asking in natural language
# Adding a future runtime: add a case to print_launch_hints().
print_launch_hints() {
  has_runtime claude && echo "  Claude Code: run /setup-wizard"
  has_runtime codex  && echo "  Codex CLI:   ask it to run the setup-wizard skill"
}

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
  echo "Next — open the project and start the wizard:"
  print_launch_hints
else
  echo ""
  echo "Done. AIDevTeamForge installed."
  echo "Next — open the project and start the wizard:"
  print_launch_hints
fi
