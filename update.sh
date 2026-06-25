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
ONLY_CMD=""   # --only <command>: surgical single-command delivery (see below)
TARGET_DIR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --force)   FORCE=true; shift ;;
    --only)    ONLY_CMD="${2:-}"; shift; if [ "$#" -gt 0 ]; then shift; fi ;;
    --only=*)  ONLY_CMD="${1#--only=}"; shift ;;
    -*)        err "Unknown flag: $1"; exit 1 ;;
    *)         TARGET_DIR="$1"; shift ;;
  esac
done

TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$TEMPLATE_DIR/scripts/constitution-drift-check.sh"

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

# ── Surgical mode: --only <command> ─────────────────────────────────────────
# Re-emit a SINGLE command + overwrite its helper subpackage, skipping the
# manifest-driven sync, three-way merges, and the version-marker bump. Same
# bounded set as `install.sh --only`. Needs no jq (no JSON merge) and does no
# placeholder substitution. Composes with --dry-run / --force.
if [ -n "$ONLY_CMD" ]; then
  PY=""
  if command -v python3 >/dev/null 2>&1; then PY="python3"
  elif command -v py >/dev/null 2>&1; then PY="py -3"
  elif command -v python >/dev/null 2>&1; then PY="python"; fi
  if [ -z "$PY" ]; then err "Python 3 is required to emit the command."; exit 1; fi

  cmd_u="$(printf '%s' "$ONLY_CMD" | tr '-' '_')"

  header "Surgical update — only '$ONLY_CMD'"
  info "Target: $TARGET_DIR"
  overwrt "RE-EMIT    .claude/commands/$ONLY_CMD.md (+ references/)"
  if [ -d "$TEMPLATE_DIR/src/devforge/lib/_${cmd_u}" ]; then
    overwrt "OVERWRITE  .devforge/lib/_${cmd_u}/"
  fi
  if [ -d "$TEMPLATE_DIR/src/devforge/lib/_shared" ]; then
    overwrt "OVERWRITE  .devforge/lib/_shared/ (shared deps refactored helpers import)"
  fi
  for _l in "${cmd_u}_helper" "${cmd_u}_helper.py"; do
    if [ -f "$TEMPLATE_DIR/src/devforge/lib/$_l" ]; then
      overwrt "OVERWRITE  .devforge/lib/$_l"
    fi
  done
  echo ""

  if [ "$DRY_RUN" = true ]; then
    info "Dry run — no files modified."
    exit 0
  fi
  if [ "$FORCE" != true ]; then
    printf "Apply surgical update for '%s'? [y/N] " "$ONLY_CMD"
    read -r confirm
    case "$confirm" in [Yy]*) ;; *) info "Aborted."; exit 0 ;; esac
  fi

  if ! $PY "$TEMPLATE_DIR/scripts/emitters/claude.py" \
       --src "$TEMPLATE_DIR/src" --target "$TARGET_DIR" --only "$ONLY_CMD"; then
    err "Emit failed for '$ONLY_CMD' (not a promoted command?)."
    exit 1
  fi
  added "Re-emitted: .claude/commands/$ONLY_CMD.md (+ references/)"

  if [ -d "$TEMPLATE_DIR/src/devforge/lib/_${cmd_u}" ]; then
    rm -rf "$TARGET_DIR/.devforge/lib/_${cmd_u}"
    cp -R "$TEMPLATE_DIR/src/devforge/lib/_${cmd_u}" "$TARGET_DIR/.devforge/lib/_${cmd_u}"
    added "Overwrote: .devforge/lib/_${cmd_u}/"
  fi
  # Refactored helpers import from .devforge/lib/_shared/ — ship it too, or the
  # target's helper cannot import. Framework-owned, clean replace.
  if [ -d "$TEMPLATE_DIR/src/devforge/lib/_shared" ]; then
    rm -rf "$TARGET_DIR/.devforge/lib/_shared"
    cp -R "$TEMPLATE_DIR/src/devforge/lib/_shared" "$TARGET_DIR/.devforge/lib/_shared"
    rm -rf "$TARGET_DIR/.devforge/lib/_shared/__pycache__"
    added "Overwrote: .devforge/lib/_shared/"
  fi
  for _l in "${cmd_u}_helper" "${cmd_u}_helper.py"; do
    if [ -f "$TEMPLATE_DIR/src/devforge/lib/$_l" ]; then
      cp "$TEMPLATE_DIR/src/devforge/lib/$_l" "$TARGET_DIR/.devforge/lib/$_l"
      added "Overwrote: .devforge/lib/$_l"
    fi
  done
  if [ -f "$TARGET_DIR/.devforge/lib/${cmd_u}_helper" ]; then
    chmod +x "$TARGET_DIR/.devforge/lib/${cmd_u}_helper"
  fi

  header "Surgical update complete"
  info "Delivered '$ONLY_CMD' only — manifest sync, merges, and the version marker were skipped."
  exit 0
fi

# ── Check for jq (required for JSON merging) ───────────────────────────────
if ! command -v jq >/dev/null 2>&1; then
  err "jq is required for JSON merging but was not found."
  err "Install it with:  brew install jq  (macOS)  or  apt install jq  (Linux)"
  exit 1
fi

# ── Detect Python 3 (required for placeholder substitution + agent regen) ──
PYTHON3_CMD=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON3_CMD="python3"
elif command -v py >/dev/null 2>&1; then
  PYTHON3_CMD="py"
elif command -v python >/dev/null 2>&1 && [ "$(python -c 'import sys; print(sys.version_info[0])' 2>/dev/null)" = "3" ]; then
  PYTHON3_CMD="python"
fi
if [ -z "$PYTHON3_CMD" ]; then
  err "Python 3 is required (placeholder substitution + agent regeneration) but was not found."
  exit 1
fi

# ── Load manifest ──────────────────────────────────────────────────────────
MANIFEST="$TEMPLATE_DIR/src/manifest.json"
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

# Constitution drift check (plan 44) — runs BEFORE the equal-version bail so a
# same-version-but-drifted install (code byte-current, constitution stale) is
# still caught. WARN-ONLY + fail-soft; never blocks the update.
forge_check_constitution_drift "$TARGET_DIR" "$TEMPLATE_DIR"

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
PROJECT_CONFIG="$TARGET_DIR/.devforge/project-config.json"
HAS_CONFIG=false

# Substitute {{PLACEHOLDER}} variables in a file via the framework renderer.
# Delegates to `configure_helper substitute-file` so the {{KEY}} map (singular
# <-> plural aliases, the PACKAGE_STACKS table, and identity passthroughs like
# {{UPPERCASE}}) stays single-sourced in _render.py instead of being
# re-implemented as a drift-prone literal jq loop here. The legacy second
# positional arg (config path) is accepted but ignored. Returns the helper's
# exit code: 0 = fully substituted (known/identity placeholders only),
# 2 = an unknown placeholder remains (file left unchanged), 1 = config/file error.
substitute_placeholders() {
  local file="$1"
  "$PYTHON3_CMD" "$TEMPLATE_DIR/src/devforge/lib/configure_helper.py" \
    --devforge-dir "$TARGET_DIR/.devforge" --install-root "$TARGET_DIR" \
    substitute-file --file "$file"
}

# Check for project config. It is a render artifact (rebuilt by /configure from
# .devforge/configure.yaml + .devforge/init.yaml). If it is missing but the
# source configure.yaml exists, rebuild it via the renderer — the single source
# of truth — rather than scraping the old flat format out of CLAUDE.md.
if [ -f "$PROJECT_CONFIG" ]; then
  HAS_CONFIG=true
elif [ -f "$TARGET_DIR/.devforge/configure.yaml" ]; then
  warn "No .devforge/project-config.json — rebuilding from .devforge/configure.yaml"
  if "$PYTHON3_CMD" "$TEMPLATE_DIR/src/devforge/lib/configure_helper.py" \
       --devforge-dir "$TARGET_DIR/.devforge" --install-root "$TARGET_DIR" \
       render-config >/dev/null 2>&1 && [ -f "$PROJECT_CONFIG" ]; then
    HAS_CONFIG=true
    added "Rebuilt .devforge/project-config.json"
  else
    warn "Could not rebuild project-config.json — skipping placeholder substitution."
    warn "Run /configure to populate .devforge/configure.yaml + project-config.json"
  fi
else
  warn "No .devforge config found — skipping placeholder substitution."
  warn "Run /configure to populate .devforge/configure.yaml + project-config.json"
fi

# Validate config values — warn about placeholder-in-placeholder
if [ "$HAS_CONFIG" = true ]; then
  bad_keys="$(jq -r 'to_entries[] | select(.value | test("\\{\\{[A-Z_]+\\}\\}")) | .key' "$PROJECT_CONFIG" 2>/dev/null || true)"
  if [ -n "$bad_keys" ]; then
    warn "project-config.json has unresolved placeholders in: $bad_keys"
    warn "These values will not substitute correctly. Fix them or re-run /configure"
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

# ── Expand templateOwned.files[] into source\ttarget pairs ────────────────
# Post-reshape, manifest pairs source (template repo path, e.g. src/commands/X.md)
# with target (installed path, e.g. .claude/commands/X.md). Glob patterns (scripts/**)
# expand against the template dir.
expand_templateOwned_pairs() {
  local pair_count
  pair_count="$(jq -r '.templateOwned.files | length' "$MANIFEST")"
  local i=0
  while [ "$i" -lt "$pair_count" ]; do
    local src_path tgt_path
    src_path="$(jq -r ".templateOwned.files[$i].source" "$MANIFEST")"
    tgt_path="$(jq -r ".templateOwned.files[$i].target" "$MANIFEST")"
    case "$src_path" in
      *"**"*)
        local src_base="${src_path%%/\*\*}"
        local tgt_base="${tgt_path%%/\*\*}"
        if [ -d "$TEMPLATE_DIR/$src_base" ]; then
          find "$TEMPLATE_DIR/$src_base" -type f 2>/dev/null | while IFS= read -r fp; do
            local rel="${fp#$TEMPLATE_DIR/$src_base/}"
            printf "%s\t%s\n" "$src_base/$rel" "$tgt_base/$rel"
          done
        fi
        ;;
      *)
        if [ -f "$TEMPLATE_DIR/$src_path" ]; then
          printf "%s\t%s\n" "$src_path" "$tgt_path"
        fi
        ;;
    esac
    i=$((i + 1))
  done
}

# ── Read pattern lists from manifest ───────────────────────────────────────
PROJECT_OWNED_PATTERNS="$(jq -r '.projectOwned.patterns[]' "$MANIFEST")"
COPY_IF_MISSING_PATTERNS="$(jq -r '.copyIfMissing.patterns[]' "$MANIFEST")"
MERGE_FILES="$(jq -r '.mergeFiles.files | keys[]' "$MANIFEST")"
DERIVED_COUNT="$(jq -r '.templateDerived.mappings | length' "$MANIFEST")"

# ── Build file lists ───────────────────────────────────────────────────────
# TEMPLATE_OWNED_FILES now contains tab-separated "source\ttarget" pairs.
TEMPLATE_OWNED_FILES="$(expand_templateOwned_pairs)"
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

  if [ "$src_path" = "generated:agents" ]; then
    # Enumerate agents from installed snapshot in .devforge/template/
    # Only agents that exist in target (project chose which to install)
    if [ -d "$TARGET_DIR/.devforge/template/$tgt_path" ]; then
      find "$TARGET_DIR/.devforge/template/$tgt_path" -name "*.md" -type f | while IFS= read -r fp; do
        name="$(basename "$fp")"
        tgt_rel="$tgt_path/$name"
        if [ -f "$TARGET_DIR/$tgt_rel" ]; then
          printf "AGENT\t%s\t%s\t%s\n" "$name" "$tgt_rel" "$i"
        fi
      done
    fi
  elif [ "$src_path" = "generated:coreLLM" ]; then
    # Map sentinel to actual source file; AGENTS.md (Codex) is dropped
    real_src="src/CLAUDE.md"
    tgt_rel="$tgt_path"
    if [ "$tgt_rel" = "CLAUDE.md" ] && [ -f "$TEMPLATE_DIR/$real_src" ]; then
      if [ -f "$TARGET_DIR/$tgt_rel" ]; then
        printf "%s\t%s\t%s\n" "$real_src" "$tgt_rel" "$i"
      else
        printf "MISSING\t%s\t%s\t%s\n" "$real_src" "$tgt_rel" "$i"
      fi
    fi
  elif [ -f "$TEMPLATE_DIR/$src_path" ]; then
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

# ── Agent delivery: new + removed (FIX C) ──────────────────────────────────
# The generated:agents three-way merge above only touches agents present in the
# installed snapshot (.devforge/template/.claude/agents) AND live in the target.
# That correctly skips agents the user pruned via /configure, but it can neither
# DELIVER a genuinely-new framework agent (absent from the old snapshot) nor
# PRUNE a framework-removed one. Compute both sets here against the union of
# {current src/agents roster, snapshot}. AGENTS_TGT_DIR is the install target
# for generated:agents (always .claude/agents per the manifest).
AGENTS_TGT_DIR=".claude/agents"
AGENTS_SNAP_DIR="$TARGET_DIR/.devforge/template/$AGENTS_TGT_DIR"

# NEW agents: in the current roster (src/agents/*.md) but NOT in the snapshot.
# An agent absent from the snapshot was not installed last time → if it is also
# absent from the live target it is genuinely new (the user could not have
# pruned what never shipped). Install it.
NEW_AGENTS=""
if [ -d "$TEMPLATE_DIR/src/agents" ]; then
  NEW_AGENTS="$(for af in "$TEMPLATE_DIR/src/agents/"*.md; do
    [ -f "$af" ] || continue
    name="$(basename "$af")"
    if [ ! -f "$AGENTS_SNAP_DIR/$name" ]; then
      echo "$name"
    fi
  done)"
fi

# REMOVED agents: present in the snapshot but NOT in the current roster →
# framework-removed. Prune from both the live target and the snapshot.
REMOVED_AGENTS=""
if [ -d "$AGENTS_SNAP_DIR" ]; then
  REMOVED_AGENTS="$(for sf in "$AGENTS_SNAP_DIR/"*.md; do
    [ -f "$sf" ] || continue
    name="$(basename "$sf")"
    if [ ! -f "$TEMPLATE_DIR/src/agents/$name" ]; then
      echo "$name"
    fi
  done)"
fi

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

# Overwrite (templateOwned) — display target path for each pair
OVERWRITE_COUNT=0
echo "$TEMPLATE_OWNED_FILES" | while IFS=$'\t' read -r src tgt; do
  [ -z "$src" ] && continue
  overwrt "OVERWRITE  $tgt"
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
  entry_type="$(printf '%s' "$line" | cut -f1)"
  if [ "$entry_type" = "AGENT" ]; then
    agent_name="$(printf '%s' "$line" | cut -f2)"
    tgt="$(printf '%s' "$line" | cut -f3)"
    # A snapshot+live agent dropped from the roster is reported as PRUNE below;
    # suppress the redundant THREE-WAY MERGE line for it (Finding 2).
    if printf '%s\n' "$REMOVED_AGENTS" | grep -qxF "$agent_name"; then
      continue
    fi
  else
    tgt="$(printf '%s' "$line" | cut -f2)"
  fi
  if [ -f "$TARGET_DIR/.devforge/template/$tgt" ]; then
    merged "THREE-WAY MERGE  $tgt (template diff applied, project customizations preserved)"
  else
    info "BASELINE INIT  $tgt (snapshot will be saved; future updates will three-way merge)"
  fi
done

# New framework agents to install (FIX C)
echo "$NEW_AGENTS" | while IFS= read -r name; do
  [ -z "$name" ] && continue
  added "ADD (new agent)  $AGENTS_TGT_DIR/$name"
done

# Framework-removed agents to prune (FIX C)
echo "$REMOVED_AGENTS" | while IFS= read -r name; do
  [ -z "$name" ] && continue
  overwrt "PRUNE  $AGENTS_TGT_DIR/$name"
done

# Removed/leftover commands to prune (FIX B) — compute the canonical command set
# from the emitter and flag any *.md directly under .claude/commands/ that is no
# longer canonical. Guard on Python; the emitter step already warns when absent.
CANONICAL_COMMANDS=""
if [ -n "$PYTHON3_CMD" ]; then
  CANONICAL_COMMANDS="$($PYTHON3_CMD "$TEMPLATE_DIR/scripts/emitters/claude.py" --list 2>/dev/null || true)"
fi
if [ -n "$PYTHON3_CMD" ] && [ -d "$TARGET_DIR/.claude/commands" ]; then
  for cf in "$TARGET_DIR/.claude/commands/"*.md; do
    [ -f "$cf" ] || continue
    cname="$(basename "$cf" .md)"
    if ! printf '%s\n' "$CANONICAL_COMMANDS" | grep -qxF "$cname"; then
      overwrt "PRUNE  .claude/commands/$cname.md"
    fi
  done
fi

# Stale helpers to prune (FIX D)
if [ -d "$TARGET_DIR/.devforge/lib" ]; then
  find "$TARGET_DIR/.devforge/lib" -type f -not -path '*/__pycache__/*' 2>/dev/null | { while IFS= read -r fp; do
    rel="${fp#"$TARGET_DIR"/.devforge/lib/}"
    if [ ! -e "$TEMPLATE_DIR/src/devforge/lib/$rel" ]; then
      overwrt "PRUNE  .devforge/lib/$rel"
    fi
  done; } || true
fi

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

echo "$TEMPLATE_OWNED_FILES" | while IFS=$'\t' read -r src tgt; do
  [ -z "$src" ] && continue
  mkdir -p "$TARGET_DIR/$(dirname "$tgt")"
  cp "$TEMPLATE_DIR/$src" "$TARGET_DIR/$tgt"
  overwrt "Overwritten: $tgt"
done

# ── Execute: restore executable bits on shipped scripts (FIX E) ────────────
# The templateOwned apply loop uses plain `cp` (no -p), which drops the
# executable bit. The CBM hook scripts (.claude/hooks/*) and the opt-in
# git-hook templates (.devforge/templates/git-hooks/*.sh) must stay runnable.
if [ -d "$TARGET_DIR/.claude/hooks" ]; then
  for _hk in "$TARGET_DIR/.claude/hooks/"*; do
    [ -f "$_hk" ] && chmod +x "$_hk"
  done
fi
if [ -d "$TARGET_DIR/.devforge/templates/git-hooks" ]; then
  for _gh in "$TARGET_DIR/.devforge/templates/git-hooks/"*.sh; do
    [ -f "$_gh" ] && chmod +x "$_gh"
  done
fi

# ── Execute: prune removed helpers + restore launcher bits (FIX D) ─────────
# .devforge/lib/ is 100% framework-owned (manifest src/devforge/lib/** → .devforge/lib/**).
# The templateOwned loop OVERWRITES every current helper but never deletes
# helpers the framework removed (e.g. onboard_helper). Mirror the source: any
# file under .devforge/lib/ with no counterpart under src/devforge/lib/ is
# stale and pruned. __pycache__ dirs are stripped wholesale (never reported).
if [ -d "$TARGET_DIR/.devforge/lib" ]; then
  find "$TARGET_DIR/.devforge/lib" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
  find "$TARGET_DIR/.devforge/lib" -type f 2>/dev/null | { while IFS= read -r fp; do
    rel="${fp#"$TARGET_DIR"/.devforge/lib/}"
    if [ ! -e "$TEMPLATE_DIR/src/devforge/lib/$rel" ]; then
      rm -f "$fp"
      overwrt "Pruned: .devforge/lib/$rel"
    fi
  done; } || true
  # Remove now-empty subdirs left behind (e.g. a fully-pruned helper subpackage
  # like _onboard/) so .devforge/lib/ exactly mirrors the source layout.
  find "$TARGET_DIR/.devforge/lib" -mindepth 1 -type d -empty -delete 2>/dev/null || true
  # cp drops the executable bit on the extension-less launcher scripts.
  for _ln in "$TARGET_DIR/.devforge/lib/"*_helper; do
    [ -f "$_ln" ] && chmod +x "$_ln"
  done
fi

# ── Execute: templateDerived (update generated files from templates) ───────
# Three-way merge for template-derived files:
# - baseline = .devforge/template/<path> (snapshot of last installed version, raw/un-substituted)
# - new      = re-generated / sourced template (substituted with current project config)
# - current  = live file in target (may have project customizations)
# Applies only the template diff (baseline→new) to current, preserving project customizations.
# Baseline is created at install time, so the first update can merge immediately (no gap).

# Pre-generate agents once if any AGENT work exists this run — either existing
# snapshot agents to three-way merge OR new framework agents to install (FIX C).
REGEN_AGENTS_DIR=""
AGENT_WORK=false
if echo "$DERIVED_UPDATE" | grep -q '^AGENT	'; then AGENT_WORK=true; fi
if [ -n "$NEW_AGENTS" ]; then AGENT_WORK=true; fi
if [ "$AGENT_WORK" = true ]; then
  if [ -n "$PYTHON3_CMD" ]; then
    REGEN_AGENTS_DIR="$(mktemp -d)"
    if ! $PYTHON3_CMD "$TEMPLATE_DIR/scripts/generate-agents.py" \
         --src "$TEMPLATE_DIR/src/agents" \
         --target "$REGEN_AGENTS_DIR" >/dev/null 2>&1; then
      warn "Agent regeneration failed — agent files will not be updated this run"
      rm -rf "$REGEN_AGENTS_DIR"
      REGEN_AGENTS_DIR=""
    fi
  else
    warn "Python 3 not found — agent files will not be updated this run"
  fi
fi

echo "$DERIVED_UPDATE" | while IFS= read -r line; do
  [ -z "$line" ] && continue

  # Parse entry: AGENT entries have an extra leading type field
  entry_type="$(printf '%s' "$line" | cut -f1)"
  if [ "$entry_type" = "AGENT" ]; then
    agent_name="$(printf '%s' "$line" | cut -f2)"
    tgt="$(printf '%s' "$line" | cut -f3)"
  else
    src="$(printf '%s' "$line" | cut -f1)"
    tgt="$(printf '%s' "$line" | cut -f2)"
  fi

  mkdir -p "$TARGET_DIR/$(dirname "$tgt")"
  baseline_raw="$TARGET_DIR/.devforge/template/$tgt"

  # Build "new" substituted version
  new_tpl="$(mktemp)"
  if [ "$entry_type" = "AGENT" ]; then
    if [ -z "$REGEN_AGENTS_DIR" ]; then
      rm -f "$new_tpl"; continue
    fi
    regen_src="$REGEN_AGENTS_DIR/.claude/agents/$agent_name"
    if [ ! -f "$regen_src" ]; then
      warn "Regenerated agent not found: $agent_name — skipping"
      rm -f "$new_tpl"; continue
    fi
    cp "$regen_src" "$new_tpl"
  else
    cp "$TEMPLATE_DIR/$src" "$new_tpl"
  fi
  # Substitute via the renderer; skip the file if it cannot fully substitute
  # (exit 2 = unknown placeholder, exit 1 = config/file error). The renderer
  # knows {{UPPERCASE}} is an identity passthrough, so a clean file exits 0 —
  # do NOT grep for {{...}} here (that would false-positive on {{UPPERCASE}}).
  if [ "$HAS_CONFIG" = true ]; then
    if ! substitute_placeholders "$new_tpl"; then
      warn "Skipped $tgt — unresolved placeholders (check .devforge/project-config.json)"
      rm -f "$new_tpl"; continue
    fi
  else
    warn "Skipped $tgt — no .devforge/project-config.json; run /configure"
    rm -f "$new_tpl"; continue
  fi

  # Three-way merge against .devforge/template/ baseline
  if [ -f "$baseline_raw" ]; then
    baseline_sub="$(mktemp)"
    cp "$baseline_raw" "$baseline_sub"
    # Best-effort substitution of the merge baseline (ignore exit: a removed
    # legacy placeholder leaving it partly raw degrades to a safe merge
    # conflict, never a hard abort under set -e).
    if [ "$HAS_CONFIG" = true ]; then
      substitute_placeholders "$baseline_sub" || true
    fi

    tmp_current="$(mktemp)"
    cp "$TARGET_DIR/$tgt" "$tmp_current"
    if git merge-file "$tmp_current" "$baseline_sub" "$new_tpl" 2>/dev/null; then
      mv "$tmp_current" "$TARGET_DIR/$tgt"
      merged "Three-way merged: $tgt"
      # Refresh snapshot with new raw (un-substituted) template
      if [ "$entry_type" = "AGENT" ]; then
        cp "$REGEN_AGENTS_DIR/.claude/agents/$agent_name" "$baseline_raw"
      else
        cp "$TEMPLATE_DIR/$src" "$baseline_raw"
      fi
    else
      rm -f "$tmp_current"
      warn "Merge conflicts in $tgt — file unchanged, review template changes manually"
    fi
    rm -f "$baseline_sub"
  else
    # No snapshot yet (old install before this feature) — save baseline, leave file unchanged
    mkdir -p "$(dirname "$baseline_raw")"
    if [ "$entry_type" = "AGENT" ]; then
      cp "$REGEN_AGENTS_DIR/.claude/agents/$agent_name" "$baseline_raw"
    else
      cp "$TEMPLATE_DIR/$src" "$baseline_raw"
    fi
    info "Snapshot saved for $tgt (file unchanged — future updates will three-way merge)"
  fi

  rm -f "$new_tpl"
done

# ── Execute: install NEW framework agents (FIX C) ──────────────────────────
# An agent in the current roster but absent from the snapshot is genuinely new
# (devils-advocate, qa-reviewer, …). Copy the regenerated+substituted file into
# the live target AND write the raw regenerated file into the snapshot so future
# runs three-way merge it. Same substitution + unresolved-placeholder guard as
# the merge path. Requires REGEN_AGENTS_DIR; if regen failed it was already warned.
echo "$NEW_AGENTS" | while IFS= read -r name; do
  [ -z "$name" ] && continue
  if [ -z "$REGEN_AGENTS_DIR" ]; then continue; fi
  regen_src="$REGEN_AGENTS_DIR/.claude/agents/$name"
  if [ ! -f "$regen_src" ]; then
    warn "Regenerated agent not found: $name — skipping new-agent install"
    continue
  fi
  new_agent="$(mktemp)"
  cp "$regen_src" "$new_agent"
  if [ "$HAS_CONFIG" = true ]; then
    substitute_placeholders "$new_agent" || true
  fi
  # First-write semantics (Finding 1): a new framework agent that a new command
  # depends on (e.g. devils-advocate → /grill) MUST always land. Unlike the
  # three-way-merge path, we do NOT skip on unresolved placeholders — install.sh
  # ships agents with placeholders intact for the later /configure to fill, and
  # an unconfigured target already expects unresolved placeholders everywhere.
  # Write it anyway; the next /configure substitutes it.
  mkdir -p "$TARGET_DIR/$AGENTS_TGT_DIR"
  cp "$new_agent" "$TARGET_DIR/$AGENTS_TGT_DIR/$name"
  if grep -q '{{[A-Z_]*}}' "$new_agent"; then
    warn "Installed new agent $AGENTS_TGT_DIR/$name with unresolved placeholders — run /configure to populate them."
  else
    added "Installed new agent: $AGENTS_TGT_DIR/$name"
  fi
  rm -f "$new_agent"
  # Seed the snapshot with the raw (un-substituted) regenerated file so future
  # updates three-way merge this agent.
  mkdir -p "$AGENTS_SNAP_DIR"
  cp "$regen_src" "$AGENTS_SNAP_DIR/$name"
done

# ── Execute: prune framework-removed agents (FIX C) ────────────────────────
# An agent in the snapshot but absent from the current roster was removed from
# the framework. Delete it from both the live target and the snapshot.
echo "$REMOVED_AGENTS" | while IFS= read -r name; do
  [ -z "$name" ] && continue
  rm -f "$TARGET_DIR/$AGENTS_TGT_DIR/$name"
  rm -f "$AGENTS_SNAP_DIR/$name"
  overwrt "Pruned removed agent: $AGENTS_TGT_DIR/$name"
done

# Cleanup agent regeneration temp dir
if [ -n "$REGEN_AGENTS_DIR" ]; then
  rm -rf "$REGEN_AGENTS_DIR"
fi

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

# ── Execute: re-emit promoted dir-shaped commands ──────────────────────────
# manifest.json's mergeFiles + templateOwned cover flat command files only.
# Promoted dir-shaped commands (init-forge, generate-docs, configure,
# constitute, research, …) live at src/commands/<name>/main.md +
# (optional) references/ and are
# emitted to .claude/commands/<name>.md by scripts/emitters/claude.py.
# Without re-running the emitter, edits to dir-shaped command sources never
# propagate to existing targets — install.sh emits them once, update.sh
# previously skipped them.
#
# Overwrite semantics here are deliberate: commands are framework-owned
# (matches templateOwned policy). User-modified target commands are NOT
# preserved across updates. Project customizations live in CLAUDE.md /
# constitution.md / agents — those still three-way merge upstream.
if [ -n "$PYTHON3_CMD" ]; then
  if $PYTHON3_CMD "$TEMPLATE_DIR/scripts/emitters/claude.py" \
       --src "$TEMPLATE_DIR/src" \
       --target "$TARGET_DIR" >/dev/null 2>&1; then
    added "Re-emitted promoted commands (init-forge, generate-docs, configure, constitute, research, …)"
  else
    warn "Promoted-command re-emit failed — dir-shaped commands may be stale"
  fi
else
  warn "Python 3 not found — promoted commands will not be re-emitted this run"
fi

# ── Execute: prune removed commands (FIX B) ────────────────────────────────
# After the emitter re-delivers the canonical command set, remove any *.md
# directly under .claude/commands/ whose basename is no longer canonical
# (dead commands like onboard / setup-wizard) along with its references dir.
# Guard on Python — the emitter step above already warned if it is missing.
if [ -n "$PYTHON3_CMD" ] && [ -d "$TARGET_DIR/.claude/commands" ]; then
  canon_cmds="$($PYTHON3_CMD "$TEMPLATE_DIR/scripts/emitters/claude.py" --list 2>/dev/null || true)"
  if [ -n "$canon_cmds" ]; then
    for cf in "$TARGET_DIR/.claude/commands/"*.md; do
      [ -f "$cf" ] || continue
      cname="$(basename "$cf" .md)"
      if ! printf '%s\n' "$canon_cmds" | grep -qxF "$cname"; then
        rm -f "$cf"
        if [ -d "$TARGET_DIR/.claude/commands/$cname" ]; then
          rm -rf "$TARGET_DIR/.claude/commands/$cname"
        fi
        overwrt "Pruned command: .claude/commands/$cname.md"
      fi
    done
  else
    warn "Could not list canonical commands — skipping command prune this run"
  fi
fi

# ── Write version marker ──────────────────────────────────────────────────
echo "$TEMPLATE_VERSION" > "$TARGET_VERSION_FILE"
added "Version marker updated: $TEMPLATE_VERSION"

# ── Report ─────────────────────────────────────────────────────────────────
header "Update complete"
info "Updated from ${BOLD}$TARGET_VERSION${NC} → ${BOLD}$TEMPLATE_VERSION${NC}"
info "Run 'git diff' in your project to review all changes."
info "CBM sync: SessionStart hook (cbm-sync-session-start) compares .devforge/cbm-last-indexed-sha to parent HEAD on every session boot and prompts Claude to call detect_changes / index_repository when stale."

# Check for major version bump and suggest migration guide
if [ "$TARGET_VERSION" != "(unknown)" ]; then
  OLD_MAJOR="${TARGET_VERSION%%.*}"
  NEW_MAJOR="${TEMPLATE_VERSION%%.*}"
  if [ "$NEW_MAJOR" -gt "$OLD_MAJOR" ] 2>/dev/null; then
    warn "This is a major version upgrade. Check CHANGELOG.md for breaking changes."
  fi
fi