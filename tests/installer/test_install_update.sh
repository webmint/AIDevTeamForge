#!/bin/bash
# Installer contract tests: install.sh, update.sh, template checksums, Forge hook merge.
# Run from anywhere:  bash tests/installer/test_install_update.sh
# Needs: git, jq, perl. Works on scratch copies only; never touches a real project.

set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
LEGACY_REF="${LEGACY_REF:-9eeff96}"   # v1.28.0 — last release without checksums
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
ok()   { PASS=$((PASS + 1)); printf "  ok    %s\n" "$1"; }
bad()  { FAIL=$((FAIL + 1)); printf "  FAIL  %s\n" "$1"; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
sha()  { if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1; else sha256sum "$1" | cut -d' ' -f1; fi; }
tree_sum() { (cd "$1" && find . -type f -not -path './.git/*' | sort | while read -r f; do printf "%s %s\n" "$(sha "$f")" "$f"; done) | sha /dev/stdin; }

# Template copy = tracked + untracked-not-ignored files of the working tree
TPL="$WORK/template"
mkdir -p "$TPL"
(cd "$REPO" && git ls-files -co --exclude-standard -z | xargs -0 tar cf - 2>/dev/null) | (cd "$TPL" && tar xf -)

echo "== checksums file is current"
cp "$TPL/.claude/template-checksums" "$WORK/sums.committed"
(cd "$TPL" && ./update.sh --write-checksums >/dev/null)
check "template-checksums matches the tree (run ./update.sh --write-checksums)" \
  'cmp -s "$WORK/sums.committed" "$TPL/.claude/template-checksums"'

echo "== fresh install"
P2="$WORK/fresh"; mkdir -p "$P2"
"$TPL/install.sh" "$P2" >/dev/null
check "storage-rules at .claude/storage-rules.md" '[ -f "$P2/.claude/storage-rules.md" ]'
check "template-checksums installed" 'cmp -s "$TPL/.claude/template-checksums" "$P2/.claude/template-checksums"'
check "forge hook fragment installed" '[ -f "$P2/.claude/hooks/forge/settings-hooks.json" ]'
check "gate.sh installed executable" '[ -x "$P2/scripts/forge/gate.sh" ]'
check "context guard installed" '[ -f "$P2/.claude/hooks/forge/context-guard.py" ]'
check "tests/ not installed" '[ ! -d "$P2/tests" ]'
check "five gate checklists installed" '[ "$(ls "$P2/.claude/checklists/"*.md | wc -l | tr -d " ")" = 5 ]'
check "independent gate partial installed" '[ -f "$P2/.claude/commands/_independent-gate.md" ]'
# partials are read by path, never run as commands: hidden from the / menu and from the model's skill listing
check "every partial is hidden from users and the model" '(for f in "$P2/.claude/commands/"_*.md; do fm="$(awk "NR==1&&!/^---\$/{exit} NR>1&&/^---\$/{exit} NR>1" "$f")"; echo "$fm" | grep -qx "disable-model-invocation: true" && echo "$fm" | grep -qx "user-invocable: false" || exit 1; done)'
check "quality scripts installed executable" 'for f in quality_profile ratchet audit-gate hub-files new-exports count-tools check-canonical-sources check-enforcement-map check-task-evidence check-decision-records; do [ -x "$P2/scripts/forge/$f.py" ] || exit 1; done'
check "no python caches installed" '[ -z "$(find "$P2" -name __pycache__ -o -name "*.pyc")" ]'
# what /setup-wizard 3.9 runs, then the gate on a fresh repo
(cd "$P2" && git init -q . && python3 scripts/forge/quality_profile.py init --integration-ref origin/main >/dev/null 2>&1)
check "binding init + validate" '(cd "$P2" && python3 scripts/forge/quality_profile.py validate >/dev/null 2>&1)'
check "binding consumers hold" '(cd "$P2" && python3 scripts/forge/quality_profile.py consumers >/dev/null 2>&1)'
check "release.md not installed" '[ ! -f "$P2/.claude/commands/release.md" ]'
check "review-pr command installed" '[ -f "$P2/.claude/commands/review-pr.md" ]'
# update.sh on settings.json shapes with no local hook paths must not stop (set -e, pipefail)
cp "$P2/.claude/hooks/forge/settings-hooks.json" "$P2/.claude/settings.json"
"$TPL/update.sh" --dry-run "$P2" < /dev/null > "$WORK/dup-forge-only.txt" 2>&1; rc=$?
check "update dry run with only Forge hooks completes" '[ $rc -eq 0 ] && grep -q "Dry run complete" "$WORK/dup-forge-only.txt"'
echo '{"permissions": {"allow": ["Read"]}}' > "$P2/.claude/settings.json"
"$TPL/update.sh" --dry-run "$P2" < /dev/null > "$WORK/dup-no-hooks.txt" 2>&1; rc=$?
check "update dry run with no hooks key completes" '[ $rc -eq 0 ] && grep -q "Dry run complete" "$WORK/dup-no-hooks.txt"'
rm -f "$P2/.claude/settings.json"
check "conduct command and autonomous partial installed" '[ -f "$P2/.claude/commands/conduct.md" ] && [ -f "$P2/.claude/commands/_autonomous-mode.md" ]'
check "push guard and wave preflight installed" '[ -f "$P2/.claude/hooks/forge/push-guard.py" ] && [ -x "$P2/scripts/forge/wave-preflight.py" ]'
check "nested-wait guard and nested-pending installed" '[ -f "$P2/.claude/hooks/forge/nested-wait-guard.py" ] && [ -x "$P2/scripts/forge/nested-pending.py" ]'
check "nested-wait guard registered for SubagentHandback" 'jq -e "[.hooks.PreToolUse[] | select(.matcher == \"SubagentHandback\") | .hooks[].command] | any(contains(\"nested-wait-guard.py\"))" "$P2/.claude/hooks/forge/settings-hooks.json" >/dev/null'
check "push guard registered in the hook fragment" 'jq -e "[.hooks.PreToolUse[].hooks[].command] | any(contains(\"push-guard.py\"))" "$P2/.claude/hooks/forge/settings-hooks.json" >/dev/null'
FORCE='{"tool_name":"Bash","tool_input":{"command":"git push --force origin spec/001-x"}}'
check "push guard inactive in interactive mode" '(printf %s "$FORCE" | CLAUDE_PROJECT_DIR="$P2" python3 "$P2/.claude/hooks/forge/push-guard.py" >/dev/null 2>&1)'
echo '{"DELIVERY_MODE": "autonomous", "DEFAULT_BRANCH": "main"}' > "$P2/.claude/project-config.json"
check "push guard denies a force push in autonomous mode" '! (printf %s "$FORCE" | CLAUDE_PROJECT_DIR="$P2" python3 "$P2/.claude/hooks/forge/push-guard.py" >/dev/null 2>&1)'
rm -f "$P2/.claude/project-config.json"

echo "== update from a legacy (pre-checksum) install"
LEG="$WORK/legacy"; mkdir -p "$LEG"
(cd "$REPO" && git archive "$LEGACY_REF") | (cd "$LEG" && tar xf -)
P1="$WORK/project"; mkdir -p "$P1"
"$LEG/install.sh" "$P1" >/dev/null
# what /setup-wizard and the project would have added
mkdir -p "$P1/.claude/hooks"
cat > "$P1/.claude/settings.json" <<'JSON'
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [ { "type": "command", "command": "python3 .claude/hooks/project-guard.py" } ] },
      { "matcher": "Read", "hooks": [ { "type": "command", "command": "python3 .claude/hooks/forge/retired.py" } ] },
      { "matcher": "Edit", "hooks": [ { "type": "command", "command": "python3 .claude/hooks/forge/fake-guard.py" },
                                      { "type": "prompt", "prompt": "project prompt hook" } ] }
    ],
    "PostToolUse": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/context-guard.py\" || true" } ] }
    ]
  },
  "permissions": { "allow": ["Read"] }
}
JSON
echo "print('project')" > "$P1/.claude/hooks/project-guard.py"
cat > "$P1/.claude/project-config.json" <<'JSON'
{"PROJECT_NAME": "demo", "PR_VIEW_COMMAND": "gh pr view <N> --json title", "PR_SEARCH_COMMAND": "gh pr list --search \"<KEY> in:title\"", "ISSUE_TRACKER": "jira"}
JSON
review_keys() { jq -c '[.PR_VIEW_COMMAND, .PR_SEARCH_COMMAND, .ISSUE_TRACKER]' "$1"; }
review_keys_before="$(review_keys "$P1/.claude/project-config.json")"
echo "echo project tool" > "$P1/scripts/my-tool.sh"
echo "# hand-ported copy" > "$P1/scripts/gate.sh"
echo "<!-- local edit -->" >> "$P1/.claude/commands/fix.md"
# a template that ships one Forge hook
cat > "$TPL/.claude/hooks/forge/settings-hooks.json" <<'JSON'
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [ { "type": "command", "command": "python3 .claude/hooks/forge/fake-guard.py" } ] }
    ]
  }
}
JSON
echo "print('forge')" > "$TPL/.claude/hooks/forge/fake-guard.py"
(cd "$TPL" && ./update.sh --write-checksums >/dev/null)

cfg_before="$(sha "$P1/.claude/project-config.json")"
echo n | "$TPL/update.sh" "$P1" > "$WORK/abort.txt" 2>&1
check "answering N leaves project-config unchanged" '[ "$cfg_before" = "$(sha "$P1/.claude/project-config.json")" ]'
before="$(tree_sum "$P1")"
"$TPL/update.sh" --dry-run "$P1" < /dev/null > "$WORK/dry.txt" 2>&1
check "dry run changes nothing" '[ "$before" = "$(tree_sum "$P1")" ]'
check "dry run flags the edited command for backup" 'grep -q "backup)  .claude/commands/fix.md" "$WORK/dry.txt"'

"$TPL/update.sh" --force "$P1" < /dev/null > "$WORK/up1.txt" 2>&1; rc=$?
check "update 1 exits 0" '[ $rc -eq 0 ]'
check "local hook duplicating a Forge hook is reported" 'grep -q "DUPLICATE  settings.json runs .*\.claude/hooks/context-guard.py" "$WORK/up1.txt"'
check "local script duplicating a Forge script is reported" 'grep -q "DUPLICATE  scripts/gate.sh" "$WORK/up1.txt"'
check "duplicates are only reported, never removed" '[ -f "$P1/scripts/gate.sh" ] && jq -e "[.hooks.PostToolUse[].hooks[].command] | any(contains(\"hooks/context-guard.py\"))" "$P1/.claude/settings.json" >/dev/null'
check "a project hook without a Forge counterpart is not reported" '! grep -q "DUPLICATE.*project-guard" "$WORK/up1.txt" && ! grep -q "DUPLICATE  scripts/my-tool.sh" "$WORK/up1.txt"'
check "project script untouched" 'grep -q "project tool" "$P1/scripts/my-tool.sh"'
check "project hook untouched" '[ -f "$P1/.claude/hooks/project-guard.py" ]'
check "fix.md now equals the template" 'cmp -s "$TPL/.claude/commands/fix.md" "$P1/.claude/commands/fix.md"'
B1="$(ls -d "$P1"/.claude/.update-backup/*/ 2>/dev/null | head -1)"
check "edited fix.md backed up with the edit" '[ -n "$B1" ] && grep -q "local edit" "$B1/.claude/commands/fix.md"'
check "storage-rules added" '[ -f "$P1/.claude/storage-rules.md" ]'
check "checksums written" 'cmp -s "$TPL/.claude/template-checksums" "$P1/.claude/template-checksums"'
check "project hook group kept" '[ "$(jq "[.hooks.PreToolUse[].hooks[] | select((.command? // \"\") | contains(\"project-guard\"))] | length" "$P1/.claude/settings.json")" = 1 ]'
check "retired forge hook group removed" '[ "$(jq "[.hooks.PreToolUse[].hooks[] | select((.command? // \"\") | contains(\"retired.py\"))] | length" "$P1/.claude/settings.json")" = 0 ]'
check "forge hook entry present exactly once" '[ "$(jq "[.hooks.PreToolUse[].hooks[] | select((.command? // \"\") | contains(\"fake-guard\"))] | length" "$P1/.claude/settings.json")" = 1 ]'
check "project prompt hook in a shared group kept" '[ "$(jq "[.hooks.PreToolUse[].hooks[] | select(.type == \"prompt\")] | length" "$P1/.claude/settings.json")" = 1 ]'
check "review keys with <N>/<KEY> kept verbatim" '[ "$(review_keys "$P1/.claude/project-config.json")" = "$review_keys_before" ]'
check "review keys raise no placeholder warning" '! grep -q "unresolved placeholders" "$WORK/up1.txt"'
check "DEFAULT_BRANCH added to project-config" '[ "$(jq -r .DEFAULT_BRANCH "$P1/.claude/project-config.json")" = main ]'
check "other settings keys kept" '[ "$(jq -c .permissions.allow "$P1/.claude/settings.json")" = "[\"Read\"]" ]'
check "checklists added on update" '[ "$(ls "$P1/.claude/checklists/"*.md | wc -l | tr -d " ")" = 5 ]'
check "quality scripts added on update" '[ -x "$P1/scripts/forge/quality_profile.py" ] && [ -x "$P1/scripts/forge/audit-gate.py" ]'

echo "== second update: local edit vs template change, idempotent hooks"
sleep 1   # distinct backup timestamp
echo "<!-- second local edit -->" >> "$P1/.claude/commands/verify.md"
sed -i.bak 's/^\*\*Gate\*\*: on/**Gate**: off/' "$P1/.claude/checklists/breakdown-gate.md" && rm -f "$P1/.claude/checklists/breakdown-gate.md.bak"
rm "$P1/.claude/checklists/test-lens.md"
echo "<!-- template change -->" >> "$TPL/.claude/commands/breakdown.md"
(cd "$TPL" && ./update.sh --write-checksums >/dev/null)
"$TPL/update.sh" --force "$P1" < /dev/null > "$WORK/up2.txt" 2>&1; rc=$?
check "update 2 exits 0" '[ $rc -eq 0 ]'
B2="$(ls -d "$P1"/.claude/.update-backup/*/ | sort | tail -1)"
check "second backup dir is new" '[ "$B1" != "$B2" ]'
check "locally edited verify.md backed up" 'grep -q "second local edit" "$B2/.claude/commands/verify.md"'
check "template-changed breakdown.md not backed up" '[ ! -f "$B2/.claude/commands/breakdown.md" ]'
check "breakdown.md updated" 'grep -q "template change" "$P1/.claude/commands/breakdown.md"'
check "unchanged fix.md not backed up again" '[ ! -f "$B2/.claude/commands/fix.md" ]'
check "forge hook entry still once" '[ "$(jq "[.hooks.PreToolUse[].hooks[] | select((.command? // \"\") | contains(\"fake-guard\"))] | length" "$P1/.claude/settings.json")" = 1 ]'
check "project-edited checklist kept" 'grep -q "^\*\*Gate\*\*: off" "$P1/.claude/checklists/breakdown-gate.md"'
check "deleted checklist restored" '[ -f "$P1/.claude/checklists/test-lens.md" ]'
check "project hook group still once" '[ "$(jq "[.hooks.PreToolUse[].hooks[] | select((.command? // \"\") | contains(\"project-guard\"))] | length" "$P1/.claude/settings.json")" = 1 ]'

echo ""
echo "passed: $PASS  failed: $FAIL"
[ "$FAIL" -eq 0 ]
