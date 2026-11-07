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
check "release.md not installed" '[ ! -f "$P2/.claude/commands/release.md" ]'

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
    ]
  },
  "permissions": { "allow": ["Read"] }
}
JSON
echo "print('project')" > "$P1/.claude/hooks/project-guard.py"
echo '{"PROJECT_NAME": "demo"}' > "$P1/.claude/project-config.json"
echo "echo project tool" > "$P1/scripts/my-tool.sh"
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
check "DEFAULT_BRANCH added to project-config" '[ "$(jq -r .DEFAULT_BRANCH "$P1/.claude/project-config.json")" = main ]'
check "other settings keys kept" '[ "$(jq -c .permissions.allow "$P1/.claude/settings.json")" = "[\"Read\"]" ]'

echo "== second update: local edit vs template change, idempotent hooks"
sleep 1   # distinct backup timestamp
echo "<!-- second local edit -->" >> "$P1/.claude/commands/verify.md"
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
check "project hook group still once" '[ "$(jq "[.hooks.PreToolUse[].hooks[] | select((.command? // \"\") | contains(\"project-guard\"))] | length" "$P1/.claude/settings.json")" = 1 ]'

echo ""
echo "passed: $PASS  failed: $FAIL"
[ "$FAIL" -eq 0 ]
