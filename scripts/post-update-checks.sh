#!/bin/bash
# Shared, framework-internal post-update advisories.
#
# Sourced by update.sh and called at the two points a user reads last: just
# before the --dry-run exit, and after the "Update complete" report. WARN-ONLY:
# both checks detect something the update itself cannot fix, print what to do,
# and NEVER mutate user files. Fail-soft: any unexpected error prints a
# "skipped" note (or nothing) and returns 0 — a check must never block update.
# Safe to call under `set -euo pipefail`.
#
#   forge_check_config_completeness — .devforge/project-config.json predates
#     keys the current configure schema renders (update.sh never re-renders an
#     existing project-config.json), so those settings stay unset until the
#     user re-runs /devforge:configure.
#   forge_check_precommit_hook — /devforge:constitute Phase 6.4 installs the
#     forcing-functions pre-commit hook as a COPY; update.sh refreshes only the
#     template under .devforge/templates/git-hooks/, so an installed copy keeps
#     its old content.
#
# The freshly-shipped TEMPLATE files are used (not the consumer's installed
# copies), mirroring scripts/constitution-drift-check.sh: on the --dry-run
# path the consumer's .devforge/lib/ is still the old code.

forge_check_config_completeness() {
  local target_dir="$1"
  local template_dir="$2"
  local helper="$template_dir/src/devforge/lib/configure_helper"
  local devforge_dir="$target_dir/.devforge"

  # Not configured yet: update.sh already tells the user to run
  # /devforge:configure on that path. Silent.
  [ -f "$devforge_dir/project-config.json" ] || return 0

  if [ ! -f "$helper" ]; then
    printf "  config completeness check skipped: helper not found at %s\n" "$helper"
    return 0
  fi

  local err_file verify_exit detail
  err_file="$(mktemp 2>/dev/null)" || {
    printf "  config completeness check skipped: mktemp failed\n"
    return 0
  }

  # `|| verify_exit=$?` keeps the failing call inside an OR-list so a caller's
  # `set -e` does NOT abort here — exit 2 (violations) is the expected case.
  verify_exit=0
  "$helper" --devforge-dir "$devforge_dir" --install-root "$target_dir" \
      verify >/dev/null 2>"$err_file" || verify_exit=$?

  if [ "$verify_exit" -eq 0 ]; then
    rm -f "$err_file"
    return 0
  fi
  if [ "$verify_exit" -ne 2 ]; then
    printf "  config completeness check skipped: helper exit %s\n" "$verify_exit"
    rm -f "$err_file"
    return 0
  fi

  # Keep only the helper's own violation lines — interpreter noise on stderr
  # (e.g. a SyntaxWarning printed on first compile) is dropped. grep exits 1
  # on no match, hence the `|| detail=""`.
  detail="$(grep -E '^(configure_helper )?verify: ' "$err_file" 2>/dev/null \
      | sed -E 's/^(configure_helper )?verify: /  • /')" || detail=""
  rm -f "$err_file"

  printf "\n⚠  Project configuration does not match this framework version (configure_helper verify):\n"
  if [ -n "$detail" ]; then
    printf "%s\n" "$detail"
  fi
  # The consequence line is printed only for the violation shape it describes:
  # a CLAUDE_TIER_* key that is absent or null resolves to `inherit` in
  # apply-models. A round-trip mismatch on a tier key carries a value, and a
  # corrupt or unreadable file is a different problem — neither gets it.
  if printf '%s\n' "$detail" | grep -qE 'missing key CLAUDE_TIER_|required field CLAUDE_TIER_[A-Z_]+ is null'; then
    printf "  A model tier reported above runs on the session's model (inherit) until it is configured.\n"
  fi
  printf "  Fix: re-run /devforge:configure, which writes .devforge/configure.yaml and renders .devforge/project-config.json.\n\n"
  return 0
}

forge_check_precommit_hook() {
  local target_dir="$1"
  local template_dir="$2"
  local template_hook="$template_dir/src/git-hooks/pre-commit-forcing-functions.sh"
  # The template's own second line — a byte-for-byte copy carries it, a
  # foreign hook does not.
  local marker="# pre-commit-forcing-functions.sh"
  local hook_path

  if [ ! -f "$template_hook" ]; then
    printf "  pre-commit hook check skipped: template not found at %s\n" "$template_hook"
    return 0
  fi
  command -v git >/dev/null 2>&1 || return 0

  # --git-path resolves the ACTIVE hook location: it honors core.hooksPath and
  # linked worktrees, and a target nested inside a parent repository resolves
  # to that repository's hook. Not a git repository → nothing to check.
  hook_path="$(git -C "$target_dir" rev-parse --git-path hooks/pre-commit 2>/dev/null)" || return 0
  [ -n "$hook_path" ] || return 0
  # The result may be relative to target_dir (the default .git/hooks/pre-commit,
  # a relative core.hooksPath, or ../.git/... for a nested target).
  case "$hook_path" in
    /*|[A-Za-z]:[\\/]*) ;;
    *) hook_path="$target_dir/$hook_path" ;;
  esac

  [ -f "$hook_path" ] || return 0
  grep -qxF "$marker" "$hook_path" 2>/dev/null || return 0
  if cmp -s "$hook_path" "$template_hook"; then
    return 0
  fi

  printf "\n⚠  Installed pre-commit hook differs from the framework's current copy:\n"
  printf "  • %s\n" "$hook_path"
  printf "  Fix: once this update is applied, and only if you have not customized the hook, re-copy it from the project root:\n"
  printf "    cp .devforge/templates/git-hooks/pre-commit-forcing-functions.sh \"%s\" && chmod +x \"%s\"\n\n" "$hook_path" "$hook_path"
  return 0
}
