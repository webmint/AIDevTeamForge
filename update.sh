#!/bin/bash
# Update a project that was installed from AIDevTeamForge.
#
# Usage:
#   ./update.sh /path/to/target-project
#   ./update.sh --dry-run /path/to/target-project
#   ./update.sh --force /path/to/target-project

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Helpers ─────────────────────────────────────────────────────────────────
info()    { printf "${CYAN}ℹ${NC}  %b\n" "$*"; }
added()   { printf "${GREEN}+${NC}  %b\n" "$*"; }
merged()  { printf "${YELLOW}~${NC}  %b\n" "$*"; }
skipped() { printf "${BLUE}⊘${NC}  %b\n" "$*"; }
overwrt() { printf "${RED}↻${NC}  %b\n" "$*"; }
warn()    { printf "${YELLOW}⚠${NC}  %b\n" "$*"; }
err()     { printf "${RED}✖${NC}  %b\n" "$*" >&2; }
header()  { printf "\n${BOLD}%b${NC}\n" "$*"; }

# ── Parse arguments ─────────────────────────────────────────────────────────
DRY_RUN=false
FORCE=false
TARGET_DIR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --force)   FORCE=true; shift ;;
    -*)        err "Unknown flag: $1"; exit 1 ;;
    *)         TARGET_DIR="$1"; shift ;;
  esac
done

TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "$TARGET_DIR" ]; then
  echo "Usage: update.sh [--dry-run] [--force] <target-project-directory>"
  echo ""
  echo "Flags:"
  echo "  --dry-run   Show what would change without making modifications"
  echo "  --force     Skip confirmation prompt"
  exit 1
fi

# Resolve to absolute path
TARGET_DIR="$(cd "$TARGET_DIR" 2>/dev/null && pwd)" || {
  err "Directory '$TARGET_DIR' does not exist."
  exit 1
}

# ── Validate target ────────────────────────────────────────────────────────
if [ ! -d "$TARGET_DIR/.claude" ]; then
  err "Target does not look like a project installed from this template."
  err "Missing .claude/ directory in: $TARGET_DIR"
  exit 1
fi

# ── Check for jq (required for JSON merging) ───────────────────────────────
if ! command -v jq >/dev/null 2>&1; then
  err "jq is required for JSON merging but was not found."
  err "Install it with:  brew install jq  (macOS)  or  apt install jq  (Linux)"
  exit 1
fi

# ── Check for perl (required for placeholder substitution) ───────────────
if ! command -v perl >/dev/null 2>&1; then
  err "perl is required for placeholder substitution but was not found."
  exit 1
fi

# ── Load manifest ──────────────────────────────────────────────────────────
MANIFEST="$TEMPLATE_DIR/.claude/template-manifest.json"
if [ ! -f "$MANIFEST" ]; then
  err "Template manifest not found at: $MANIFEST"
  exit 1
fi

TEMPLATE_VERSION="$(jq -r '.version' "$MANIFEST")"
TARGET_VERSION_FILE="$TARGET_DIR/.claude/template-version"

if [ -f "$TARGET_VERSION_FILE" ]; then
  TARGET_VERSION="$(tr -d '[:space:]' < "$TARGET_VERSION_FILE")"
else
  TARGET_VERSION="(unknown)"
fi

# ── Version info ───────────────────────────────────────────────────────────
header "AIDevTeamForge — Update"
info "Template version: ${BOLD}$TEMPLATE_VERSION${NC}"
info "Target version:   ${BOLD}$TARGET_VERSION${NC}"
info "Target path:      $TARGET_DIR"

if [ "$TEMPLATE_VERSION" = "$TARGET_VERSION" ]; then
  warn "Target is already on version $TEMPLATE_VERSION."
  if [ "$FORCE" != true ]; then
    echo ""
    printf "Continue anyway? [y/N] "
    read -r confirm
    case "$confirm" in [Yy]*) ;; *) info "Aborted."; exit 0 ;; esac
  fi
fi

# Show changelog excerpt if available
CHANGELOG="$TEMPLATE_DIR/CHANGELOG.md"
if [ -f "$CHANGELOG" ] && [ "$TARGET_VERSION" != "(unknown)" ] && [ "$TARGET_VERSION" != "$TEMPLATE_VERSION" ]; then
  header "Changelog (since $TARGET_VERSION)"
  awk -v from="$TARGET_VERSION" -v to="$TEMPLATE_VERSION" '
    /^## \[/ {
      v = $0; gsub(/^## \[|\] .*/, "", v)
      if (v == to) { printing = 1 }
      if (v == from) { printing = 0 }
    }
    printing { print }
  ' "$CHANGELOG"
  echo ""
fi

# ── Project config ────────────────────────────────────────────────────────
PROJECT_CONFIG="$TARGET_DIR/.claude/project-config.json"
HAS_CONFIG=false

# Substitute {{PLACEHOLDER}} variables in a file using project config.
# Uses perl for safe multi-line replacement via environment variables.
substitute_placeholders() {
  local file="$1"
  local config="$2"

  local keys
  keys="$(jq -r 'keys[]' "$config")"

  for key in $keys; do
    local value
    value="$(jq -r --arg k "$key" '.[$k]' "$config")"
    export "TPL_$key=$value"
    perl -i -0pe "s/\\{\\{${key}\\}\\}/\$ENV{\"TPL_${key}\"}/g" "$file"
    unset "TPL_$key"
  done
}

# One-time migration: extract project config from existing CLAUDE.md.
# Called when project-config.json doesn't exist yet.
migrate_project_config() {
  local claude_md="$TARGET_DIR/CLAUDE.md"
  local config_out="$TARGET_DIR/.claude/project-config.json"

  if [ ! -f "$claude_md" ]; then
    warn "No CLAUDE.md found — cannot extract project config."
    warn "Run /setup-wizard in your project to generate .claude/project-config.json"
    return 1
  fi

  info "Migrating: extracting project config from existing CLAUDE.md..."

  # Extract simple key-value pairs from the known **Key**: value format
  local proj_name proj_type framework language build_tool build_cmd source_root
  local architecture error_handling api_layer state_mgmt styling monorepo
  local type_check_cmd lint_cmd project_mode

  proj_name="$(grep '^\*\*Name\*\*:' "$claude_md" | sed 's/\*\*Name\*\*: *//' | head -1)"
  proj_type="$(grep '^\*\*Type\*\*:' "$claude_md" | sed 's/\*\*Type\*\*: *//' | head -1)"
  framework="$(grep '^\*\*Framework\*\*:' "$claude_md" | sed 's/\*\*Framework\*\*: *//' | head -1)"
  language="$(grep '^\*\*Language\*\*:' "$claude_md" | sed 's/\*\*Language\*\*: *//' | head -1)"
  build_tool="$(grep '^\*\*Build Tool\*\*:' "$claude_md" | sed 's/\*\*Build Tool\*\*: *//' | head -1)"
  build_cmd="$(grep '^\*\*Build Command\*\*:' "$claude_md" | sed 's/\*\*Build Command\*\*: *//' | head -1)"
  type_check_cmd="$(grep '^\*\*Type Check Command\*\*:' "$claude_md" | sed 's/\*\*Type Check Command\*\*: *//' | head -1)"
  lint_cmd="$(grep '^\*\*Lint Command\*\*:' "$claude_md" | sed 's/\*\*Lint Command\*\*: *//' | head -1)"
  source_root="$(grep '^\*\*Source Root\*\*:' "$claude_md" | sed 's/\*\*Source Root\*\*: *//' | head -1)"
  architecture="$(grep '^\*\*Pattern\*\*:' "$claude_md" | sed 's/\*\*Pattern\*\*: *//' | head -1)"
  error_handling="$(grep '^\*\*Error Handling\*\*:' "$claude_md" | sed 's/\*\*Error Handling\*\*: *//' | head -1)"
  api_layer="$(grep '^\*\*API Layer\*\*:' "$claude_md" | sed 's/\*\*API Layer\*\*: *//' | head -1)"
  state_mgmt="$(grep '^\*\*State Management\*\*:' "$claude_md" | sed 's/\*\*State Management\*\*: *//' | head -1)"
  styling="$(grep '^\*\*Styling\*\*:' "$claude_md" | sed 's/\*\*Styling\*\*: *//' | head -1)"
  monorepo="$(grep '^\*\*Monorepo\*\*:' "$claude_md" | sed 's/\*\*Monorepo\*\*: *//' | head -1)"

  # Detect project mode: check if project-config.json hint exists, else infer from source file count
  project_mode="existing"
  local src_root="${source_root:-.}"
  if [ "$src_root" != "." ]; then
    src_root="$TARGET_DIR/$src_root"
  else
    src_root="$TARGET_DIR"
  fi
  local src_count
  src_count="$(find "$src_root" -maxdepth 3 -type f \( -name '*.ts' -o -name '*.js' -o -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.vue' -o -name '*.tsx' -o -name '*.jsx' -o -name '*.svelte' \) -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/dist/*' -not -path '*/build/*' 2>/dev/null | wc -l | tr -d ' ')"
  if [ "$src_count" -le 5 ] 2>/dev/null; then
    project_mode="greenfield"
  fi

  # Fallback for type check/lint commands based on language if not found in CLAUDE.md
  if [ -z "$type_check_cmd" ] || [ "$type_check_cmd" = "N/A" ]; then
    case "$(echo "$language" | tr '[:upper:]' '[:lower:]')" in
      *typescript*) type_check_cmd="tsc --noEmit --pretty 2>&1 | head -20" ;;
      *python*)     type_check_cmd="python -m py_compile" ;;
      *go*)         type_check_cmd="go vet ./..." ;;
      *rust*)       type_check_cmd="cargo check 2>&1 | head -20" ;;
      *)            type_check_cmd="N/A" ;;
    esac
  fi
  if [ -z "$lint_cmd" ] || [ "$lint_cmd" = "N/A" ]; then
    lint_cmd="N/A"
  fi

  # Extract PROJECT_PATHS from an existing agent file (agents have ## Project Paths section)
  local project_paths=""
  local sample_agent
  sample_agent="$(find "$TARGET_DIR/.claude/agents" -name '*.md' -type f 2>/dev/null | head -1)"
  if [ -n "$sample_agent" ]; then
    project_paths="$(awk '/^## Project Paths/{found=1; next} /^## /{found=0} found{print}' "$sample_agent" | sed '/^$/d')"
  fi

  # Extract multi-line sections from CLAUDE.md
  local project_structure dev_commands agent_list
  project_structure="$(awk '/^## Project Structure/{found=1; next} /^## /{found=0} found{print}' "$claude_md")"
  dev_commands="$(awk '/^## Development Commands/{found=1; next} /^## /{found=0} found{print}' "$claude_md")"
  agent_list="$(awk '/^## Available Agents/{found=1; next} /^## /{found=0} found{print}' "$claude_md")"

  # Detect testing framework from existing agent or CLAUDE.md
  local testing=""
  if [ -f "$TARGET_DIR/.claude/agents/qa-engineer.md" ]; then
    testing="$(grep '^\*\*Testing\*\*:' "$TARGET_DIR/.claude/agents/qa-engineer.md" | sed 's/\*\*Testing\*\*: *//' | head -1)"
  fi

  # Extract agent model from existing agent frontmatter
  local agent_model=""
  if [ -n "$sample_agent" ]; then
    agent_model="$(grep '^model:' "$sample_agent" | sed 's/model: *//' | head -1)"
  fi
  : "${agent_model:=opus}"

  # Extract commit attribution rule from Commit Convention section
  local commit_attribution=""
  commit_attribution="$(awk '/^### Attribution/{found=1; next} /^### /{found=0} found{print}' "$claude_md" | sed '/^$/d')"
  # Default to no-attribution if section not found
  if [ -z "$commit_attribution" ]; then
    commit_attribution="Do NOT include any AI or Claude attribution in commits. Specifically:
- No \`Co-Authored-By\` trailers referencing Claude, AI, or Anthropic
- No \"Generated by\", \"Created by Claude\", or similar text in title or body
- Do not set or change git \`user.name\` or \`user.email\` to reference Claude or AI
- This rule overrides any system-level defaults about AI attribution in commits"
  fi

  # Build JSON using jq
  jq -n \
    --arg PROJECT_NAME "${proj_name:-N/A}" \
    --arg PROJECT_TYPE "${proj_type:-N/A}" \
    --arg FRAMEWORK "${framework:-N/A}" \
    --arg LANGUAGE "${language:-N/A}" \
    --arg BUILD_TOOL "${build_tool:-N/A}" \
    --arg BUILD_COMMAND "${build_cmd:-N/A}" \
    --arg TYPE_CHECK_COMMAND "${type_check_cmd:-N/A}" \
    --arg LINT_COMMAND "${lint_cmd:-N/A}" \
    --arg SOURCE_ROOT "${source_root:-\.}" \
    --arg PROJECT_MODE "$project_mode" \
    --arg ARCHITECTURE "${architecture:-N/A}" \
    --arg ERROR_HANDLING "${error_handling:-N/A}" \
    --arg API_LAYER "${api_layer:-N/A}" \
    --arg STATE_MANAGEMENT "${state_mgmt:-N/A}" \
    --arg STYLING "${styling:-N/A}" \
    --arg MONOREPO_TOOL "${monorepo:-N/A}" \
    --arg TESTING "${testing:-N/A}" \
    --arg PROJECT_PATHS "${project_paths:-N/A}" \
    --arg PROJECT_STRUCTURE "${project_structure:-N/A}" \
    --arg DEV_COMMANDS "${dev_commands:-N/A}" \
    --arg AGENT_LIST "${agent_list:-N/A}" \
    --arg WRAPPER_MODE_SECTION "" \
    --arg COMMIT_ATTRIBUTION "$commit_attribution" \
    --arg AGENT_MODEL "$agent_model" \
    '{
      PROJECT_NAME: $PROJECT_NAME,
      PROJECT_TYPE: $PROJECT_TYPE,
      FRAMEWORK: $FRAMEWORK,
      LANGUAGE: $LANGUAGE,
      BUILD_TOOL: $BUILD_TOOL,
      BUILD_COMMAND: $BUILD_COMMAND,
      TYPE_CHECK_COMMAND: $TYPE_CHECK_COMMAND,
      LINT_COMMAND: $LINT_COMMAND,
      SOURCE_ROOT: $SOURCE_ROOT,
      PROJECT_MODE: $PROJECT_MODE,
      ARCHITECTURE: $ARCHITECTURE,
      ERROR_HANDLING: $ERROR_HANDLING,
      API_LAYER: $API_LAYER,
      STATE_MANAGEMENT: $STATE_MANAGEMENT,
      STYLING: $STYLING,
      MONOREPO_TOOL: $MONOREPO_TOOL,
      TESTING: $TESTING,
      PROJECT_PATHS: $PROJECT_PATHS,
      PROJECT_STRUCTURE: $PROJECT_STRUCTURE,
      DEV_COMMANDS: $DEV_COMMANDS,
      AGENT_LIST: $AGENT_LIST,
      WRAPPER_MODE_SECTION: $WRAPPER_MODE_SECTION,
      COMMIT_ATTRIBUTION: $COMMIT_ATTRIBUTION,
      AGENT_MODEL: $AGENT_MODEL
    }' > "$config_out"

  info "Wrote .claude/project-config.json — please review extracted values."
  return 0
}

# Check for project config — migrate if missing
if [ -f "$PROJECT_CONFIG" ]; then
  HAS_CONFIG=true
else
  warn "No .claude/project-config.json found in target project."
  if migrate_project_config; then
    HAS_CONFIG=true
  else
    warn "Skipping placeholder substitution for agents and CLAUDE.md."
    warn "Re-run /setup-wizard to generate .claude/project-config.json"
  fi
fi

# Validate config values — warn about placeholder-in-placeholder
if [ "$HAS_CONFIG" = true ]; then
  bad_keys="$(jq -r 'to_entries[] | select(.value | test("\\{\\{[A-Z_]+\\}\\}")) | .key' "$PROJECT_CONFIG" 2>/dev/null || true)"
  if [ -n "$bad_keys" ]; then
    warn "project-config.json has unresolved placeholders in: $bad_keys"
    warn "These values will not substitute correctly. Fix them or re-run /setup-wizard"
  fi
fi

# ── Expand glob patterns to file lists ─────────────────────────────────────
# Given a base dir and a newline-separated list of glob patterns on stdin,
# print matching files (one per line). Uses find for ** patterns, direct
# listing otherwise. Compatible with bash 3.x / macOS.
expand_patterns() {
  local base_dir="$1"
  while IFS= read -r pattern; do
    [ -z "$pattern" ] && continue
    case "$pattern" in
      *"**"*)
        # Convert glob ** pattern to find arguments
        # e.g. ".claude/templates/**" → find .claude/templates -type f
        local dir_part="${pattern%%/\*\*}"
        if [ -d "$base_dir/$dir_part" ]; then
          find "$base_dir/$dir_part" -type f 2>/dev/null | while IFS= read -r fp; do
            # Strip base_dir prefix to get relative path
            echo "${fp#$base_dir/}"
          done
        fi
        ;;
      *)
        # Direct file path (no wildcards)
        if [ -f "$base_dir/$pattern" ]; then
          echo "$pattern"
        fi
        ;;
    esac
  done | sort -u
}

# ── Read pattern lists from manifest ───────────────────────────────────────
TEMPLATE_OWNED_PATTERNS="$(jq -r '.templateOwned.patterns[]' "$MANIFEST")"
PROJECT_OWNED_PATTERNS="$(jq -r '.projectOwned.patterns[]' "$MANIFEST")"
COPY_IF_MISSING_PATTERNS="$(jq -r '.copyIfMissing.patterns[]' "$MANIFEST")"
MERGE_FILES="$(jq -r '.mergeFiles.files | keys[]' "$MANIFEST")"
DERIVED_COUNT="$(jq -r '.templateDerived.mappings | length' "$MANIFEST")"

# ── Build file lists ───────────────────────────────────────────────────────
TEMPLATE_OWNED_FILES="$(echo "$TEMPLATE_OWNED_PATTERNS" | expand_patterns "$TEMPLATE_DIR")"
COPY_IF_MISSING_FILES="$(echo "$COPY_IF_MISSING_PATTERNS" | expand_patterns "$TEMPLATE_DIR")"

# Build templateDerived file list: source → target pairs (tab-separated)
# Only includes files where the target already exists in the project.
DERIVED_UPDATE=""
DERIVED_ADD=""
i=0
while [ "$i" -lt "$DERIVED_COUNT" ]; do
  src_path="$(jq -r ".templateDerived.mappings[$i].source" "$MANIFEST")"
  tgt_path="$(jq -r ".templateDerived.mappings[$i].target" "$MANIFEST")"
  strip="$(jq -r ".templateDerived.mappings[$i].strip_suffix // \"\"" "$MANIFEST")"

  if [ -f "$TEMPLATE_DIR/$src_path" ]; then
    # Single-file mapping (e.g., CLAUDE.template.md → CLAUDE.md)
    src_rel="$src_path"
    tgt_rel="$tgt_path"
    if [ -f "$TARGET_DIR/$tgt_rel" ]; then
      printf "%s\t%s\t%s\n" "$src_rel" "$tgt_rel" "$i"
    else
      printf "MISSING\t%s\t%s\t%s\n" "$src_rel" "$tgt_rel" "$i"
    fi
  elif [ -d "$TEMPLATE_DIR/$src_path" ]; then
    # Directory-based mapping (e.g., agents/)
    find "$TEMPLATE_DIR/$src_path" -type f 2>/dev/null | while IFS= read -r src_file; do
      basename="$(basename "$src_file")"
      target_name="$(echo "$basename" | sed "s/$strip//")"
      src_rel="${src_file#$TEMPLATE_DIR/}"
      tgt_rel="$tgt_path/$target_name"

      if [ -f "$TARGET_DIR/$tgt_rel" ]; then
        printf "%s\t%s\t%s\n" "$src_rel" "$tgt_rel" "$i"
      else
        printf "MISSING\t%s\t%s\t%s\n" "$src_rel" "$tgt_rel" "$i"
      fi
    done
  fi
  i=$((i + 1))
done > /tmp/update_derived_$$

DERIVED_UPDATE="$(grep -v '^MISSING' /tmp/update_derived_$$ 2>/dev/null || true)"
DERIVED_ADD="$(grep '^MISSING' /tmp/update_derived_$$ 2>/dev/null | cut -f2,3,4 || true)"
rm -f /tmp/update_derived_$$

# Filter copyIfMissing to only files that are actually missing in target
COPY_IF_MISSING_ACTUAL=""
echo "$COPY_IF_MISSING_FILES" | while IFS= read -r f; do true; done  # no-op to check
COPY_IF_MISSING_ACTUAL="$(echo "$COPY_IF_MISSING_FILES" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  if [ ! -e "$TARGET_DIR/$f" ]; then
    echo "$f"
  fi
done)"

# Filter merge files to only those that exist in both template and target
MERGE_ACTUAL=""
MERGE_ADD=""
echo "$MERGE_FILES" | while IFS= read -r f; do true; done  # no-op to check
MERGE_ACTUAL="$(echo "$MERGE_FILES" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  if [ -f "$TEMPLATE_DIR/$f" ] && [ -f "$TARGET_DIR/$f" ]; then
    echo "$f"
  fi
done)"
MERGE_ADD="$(echo "$MERGE_FILES" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  if [ -f "$TEMPLATE_DIR/$f" ] && [ ! -f "$TARGET_DIR/$f" ]; then
    echo "$f"
  fi
done)"

# ── Dry-run report ─────────────────────────────────────────────────────────
header "Plan"

# Overwrite (templateOwned)
OVERWRITE_COUNT=0
echo "$TEMPLATE_OWNED_FILES" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  overwrt "OVERWRITE  $f"
done
OVERWRITE_COUNT="$(echo "$TEMPLATE_OWNED_FILES" | grep -c . || true)"

# Merge
echo "$MERGE_ACTUAL" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  strategy="$(jq -r --arg f "$f" '.mergeFiles.files[$f].strategy' "$MANIFEST")"
  merged "MERGE ($strategy)  $f"
done

# Merge files that don't exist in target yet — just copy
echo "$MERGE_ADD" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  added "ADD (new)  $f"
done

# Copy if missing
echo "$COPY_IF_MISSING_ACTUAL" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  added "ADD (missing)  $f"
done

# Template-derived (three-way merge)
echo "$DERIVED_UPDATE" | while IFS= read -r line; do
  [ -z "$line" ] && continue
  tgt="$(echo "$line" | cut -f2)"
  tgt_dirname="$(dirname "$tgt")"
  if [ "$tgt_dirname" = "." ]; then
    baseline_dir="$TARGET_DIR/.claude/.baseline"
  else
    baseline_dir="$TARGET_DIR/$tgt_dirname/.baseline"
  fi
  baseline_name="$(basename "$tgt")"
  if [ -f "$baseline_dir/$baseline_name" ]; then
    merged "THREE-WAY MERGE  $tgt (template diff applied, project customizations preserved)"
  else
    info "BASELINE INIT  $tgt (agent unchanged — baseline saved for future three-way merges)"
  fi
done

# Skipped (projectOwned) — just list a summary
PROJECT_OWNED_FILES="$(echo "$PROJECT_OWNED_PATTERNS" | expand_patterns "$TARGET_DIR" 2>/dev/null || true)"
SKIP_COUNT="$(echo "$PROJECT_OWNED_FILES" | grep -c . || true)"
skipped "SKIP  $SKIP_COUNT project-owned file(s)"

# Meta files
added "WRITE  .claude/template-version → $TEMPLATE_VERSION"

echo ""

if [ "$DRY_RUN" = true ]; then
  info "Dry run complete — no files were modified."
  exit 0
fi

# ── Confirmation ───────────────────────────────────────────────────────────
if [ "$FORCE" != true ]; then
  printf "Apply these changes? [y/N] "
  read -r confirm
  case "$confirm" in [Yy]*) ;; *) info "Aborted."; exit 0 ;; esac
fi

# ── Execute: templateOwned (overwrite) ─────────────────────────────────────
header "Applying updates..."

echo "$TEMPLATE_OWNED_FILES" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  mkdir -p "$TARGET_DIR/$(dirname "$f")"
  cp "$TEMPLATE_DIR/$f" "$TARGET_DIR/$f"
  overwrt "Overwritten: $f"
done

# ── Execute: templateDerived (update generated files from templates) ───────
# Three-way merge for template-derived files:
# - Generates a substituted "new" template
# - If baseline exists: applies only the template diff (baseline→new) to the current file,
#   preserving all project customizations (wizard-added items, manual edits)
# - If no baseline: saves baseline for future merges, leaves current file unchanged
# - Validates no unresolved {{PLACEHOLDER}} remain before writing
echo "$DERIVED_UPDATE" | while IFS= read -r line; do
  [ -z "$line" ] && continue
  src="$(echo "$line" | cut -f1)"
  tgt="$(echo "$line" | cut -f2)"
  mkdir -p "$TARGET_DIR/$(dirname "$tgt")"

  # Generate substituted template ("new" version)
  new_agent="$(mktemp)"
  cp "$TEMPLATE_DIR/$src" "$new_agent"
  if [ "$HAS_CONFIG" = true ]; then
    substitute_placeholders "$new_agent" "$PROJECT_CONFIG"
  fi

  # Validate substitution succeeded
  if grep -q '{{[A-Z_]*}}' "$new_agent"; then
    warn "Skipped $tgt — unresolved placeholders (check project-config.json)"
    rm -f "$new_agent"
    continue
  fi

  # Three-way merge with baseline
  # Baselines stored alongside the target: .claude/agents/.baseline/ for agents,
  # .claude/.baseline/ for top-level files like CLAUDE.md
  tgt_dirname="$(dirname "$tgt")"
  if [ "$tgt_dirname" = "." ]; then
    baseline_dir="$TARGET_DIR/.claude/.baseline"
  else
    baseline_dir="$TARGET_DIR/$tgt_dirname/.baseline"
  fi
  mkdir -p "$baseline_dir"
  baseline_name="$(basename "$tgt")"
  baseline="$baseline_dir/$baseline_name"

  if [ -f "$baseline" ]; then
    # Baseline exists → three-way merge
    tmp_current="$(mktemp)"
    cp "$TARGET_DIR/$tgt" "$tmp_current"
    if git merge-file "$tmp_current" "$baseline" "$new_agent" 2>/dev/null; then
      mv "$tmp_current" "$TARGET_DIR/$tgt"
      merged "Three-way merged: $tgt"
      # Update baseline to new template version (only on successful merge)
      cp "$new_agent" "$baseline"
    else
      # Conflicts — keep current agent AND baseline unchanged so next update retries the merge
      rm -f "$tmp_current"
      warn "Merge conflicts in $tgt — agent and baseline unchanged, review template changes manually"
    fi
  else
    # No baseline → save it, leave agent unchanged
    cp "$new_agent" "$baseline"
    info "Baseline saved for $tgt (agent unchanged — future updates will three-way merge)"
  fi

  rm -f "$new_agent"
done

# ── Execute: mergeFiles ────────────────────────────────────────────────────

# Merge JSON files using union_keys strategy:
# For each top-level key specified by mergeKey, add keys from template that
# are missing in project. Project's existing keys are never touched.
merge_json_union_keys() {
  local template_file="$1"
  local target_file="$2"
  local merge_key="$3"

  # Merge: template * target, with target taking precedence.
  # jq's * (multiply/merge) recursively merges objects. By putting template
  # first and project second, project values win on conflicts.
  local result
  result="$(jq -s --arg key "$merge_key" '
    .[0] as $template | .[1] as $project |
    $project | .[$key] = ($template[$key] * $project[$key])
  ' "$template_file" "$target_file")"

  echo "$result" | jq '.' > "$target_file"
}

# Merge files using union_lines strategy:
# Add lines from template that are not already present in target.
merge_union_lines() {
  local template_file="$1"
  local target_file="$2"

  while IFS= read -r line; do
    [ -z "$line" ] && continue
    if ! grep -qxF "$line" "$target_file" 2>/dev/null; then
      echo "$line" >> "$target_file"
    fi
  done < "$template_file"
}

echo "$MERGE_ACTUAL" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  strategy="$(jq -r --arg f "$f" '.mergeFiles.files[$f].strategy' "$MANIFEST")"

  case "$strategy" in
    union_keys)
      merge_key="$(jq -r --arg f "$f" '.mergeFiles.files[$f].mergeKey' "$MANIFEST")"
      merge_json_union_keys "$TEMPLATE_DIR/$f" "$TARGET_DIR/$f" "$merge_key"
      merged "Merged (union_keys on $merge_key): $f"
      ;;
    union_lines)
      merge_union_lines "$TEMPLATE_DIR/$f" "$TARGET_DIR/$f"
      merged "Merged (union_lines): $f"
      ;;
    *)
      warn "Unknown merge strategy '$strategy' for $f — skipping"
      ;;
  esac
done

# Merge files that don't exist in target — just copy
echo "$MERGE_ADD" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  mkdir -p "$TARGET_DIR/$(dirname "$f")"
  cp "$TEMPLATE_DIR/$f" "$TARGET_DIR/$f"
  added "Added: $f"
done

# ── Execute: copyIfMissing ─────────────────────────────────────────────────
echo "$COPY_IF_MISSING_ACTUAL" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  mkdir -p "$TARGET_DIR/$(dirname "$f")"
  cp "$TEMPLATE_DIR/$f" "$TARGET_DIR/$f"
  added "Added (was missing): $f"
done

# ── Write version marker ──────────────────────────────────────────────────
echo "$TEMPLATE_VERSION" > "$TARGET_VERSION_FILE"
added "Version marker updated: $TEMPLATE_VERSION"

# ── Report ─────────────────────────────────────────────────────────────────
header "Update complete"
info "Updated from ${BOLD}$TARGET_VERSION${NC} → ${BOLD}$TEMPLATE_VERSION${NC}"
info "Run 'git diff' in your project to review all changes."

# Check for major version bump and suggest migration guide
if [ "$TARGET_VERSION" != "(unknown)" ]; then
  OLD_MAJOR="${TARGET_VERSION%%.*}"
  NEW_MAJOR="${TEMPLATE_VERSION%%.*}"
  if [ "$NEW_MAJOR" -gt "$OLD_MAJOR" ] 2>/dev/null; then
    warn "This is a major version upgrade. Check CHANGELOG.md for breaking changes."
  fi
fi