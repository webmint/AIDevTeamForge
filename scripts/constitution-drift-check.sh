#!/bin/bash
# Shared, framework-internal constitution drift check (plan 44).
#
# Sourced by update.sh (before the equal-version bail) and install.sh (the
# brownfield "leaving as-is" branch). WARN-ONLY: it detects drift between a
# freshly-shipped template and an already-constituted consumer project, then
# warns. It NEVER mutates user files — the human applies a refresh by re-running
# /constitute. This is the cheap safety net for the drift class where new
# framework law / new forcing-function rules ship as code but the constitution
# + config that activate them stay stale across version bumps.
#
# Two checks, both advisory + fail-soft (D5): any unexpected error prints a
# "skipped" note and returns 0 — the drift check must never block install/update.
#   A — universal-section drift   (forge-internal:verify-universal-defaults)
#   D — forcing-function key drift (forge-internal:verify-forcing-function-keys)
#
# Greenfield silent-skip (OQ1): if the target has no .devforge/constitute.json,
# nothing has been constituted — return silently with no output.
#
# The freshly-shipped TEMPLATE helper is used (not the consumer's installed
# helper), because update.sh runs this BEFORE it copies the new lib — the
# installed helper is still the old code and may lack the Phase-2 verb.

forge_check_constitution_drift() {
  local target_dir="$1"
  local template_dir="$2"
  local helper="$template_dir/src/devforge/lib/constitute_helper"
  local canonical="$template_dir/src/constitution.md"
  local consumer_json="$target_dir/.devforge/constitute.json"

  # OQ1 — not-yet-constituted target: nothing to drift against. Silent.
  [ -f "$consumer_json" ] || return 0

  # Fail-soft: required framework inputs absent → skip with a note, never abort.
  if [ ! -f "$helper" ]; then
    printf "  constitution drift check skipped: helper not found at %s\n" "$helper"
    return 0
  fi
  if [ ! -f "$canonical" ]; then
    printf "  constitution drift check skipped: canonical constitution.md not found\n"
    return 0
  fi

  local uni_json uni_exit ff_json ff_exit warned detail
  warned=0
  detail=""

  # Check A — universal-section drift. Exit 2 == real drift (the consumer json is
  # guaranteed present by the guard above and the canonical path is present, so
  # exit 2 is never an input-missing case for this verb).
  # `|| uni_exit=$?` keeps the failing substitution inside an OR-list so a caller's
  # `set -e` does NOT abort here — exit 2 (drift) is the expected, handled case.
  uni_exit=0
  uni_json="$("$helper" forge-internal:verify-universal-defaults \
      --consumer-path "$target_dir" --canonical-path "$canonical" 2>/dev/null)" || uni_exit=$?
  if [ "$uni_exit" -eq 2 ]; then
    local n_uni sections
    n_uni="$(printf '%s' "$uni_json" | jq -r '.findings | length' 2>/dev/null)"
    sections="$(printf '%s' "$uni_json" | jq -r '.findings[].section' 2>/dev/null \
        | sort -u | paste -sd, - 2>/dev/null)"
    [ -n "$n_uni" ] || n_uni="?"
    detail="${detail}  • universal law: ${n_uni} rule(s) drifted across sections ${sections:-unknown}\n"
    warned=1
  elif [ "$uni_exit" -ne 0 ]; then
    printf "  constitution drift check (universal sections) skipped: helper exit %s\n" "$uni_exit"
  fi

  # Check D — forcing-function key drift. Exit 2 == drift; exit 3 == consumer json
  # absent (guard above should prevent it; treat as silent-skip if a race removes
  # it). Any other nonzero is unexpected → fail-soft note.
  # Same set -e guard as Check A — exit 2 (drift) / 3 (no consumer json) are handled.
  ff_exit=0
  ff_json="$("$helper" forge-internal:verify-forcing-function-keys \
      --consumer-path "$target_dir" 2>/dev/null)" || ff_exit=$?
  if [ "$ff_exit" -eq 2 ]; then
    local n_ff rules
    rules="$(printf '%s' "$ff_json" | jq -r '.missing_rules | join(", ")' 2>/dev/null)"
    n_ff="$(printf '%s' "$ff_json" | jq -r '.missing_rules | length' 2>/dev/null)"
    [ -n "$n_ff" ] || n_ff="?"
    detail="${detail}  • forcing-function config: ${n_ff} rule(s) missing (${rules:-unknown})\n"
    warned=1
  elif [ "$ff_exit" -ne 0 ] && [ "$ff_exit" -ne 3 ]; then
    printf "  constitution drift check (forcing functions) skipped: helper exit %s\n" "$ff_exit"
  fi

  if [ "$warned" -eq 1 ]; then
    printf "\n⚠  Constitution out of date — framework law has changed since this project was constituted:\n"
    printf "%b" "$detail"
    printf "  Fix: re-run /devforge:constitute to re-synthesize constitution.md + forcing-function config.\n\n"
  fi
  return 0
}
