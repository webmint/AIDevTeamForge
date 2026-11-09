#!/bin/bash
# Tests for scripts/forge/gate.sh. Run: bash tests/scripts/test_gate.sh
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK" && git init -q .
mkdir -p scripts/forge && cp "$REPO/scripts/forge/gate.sh" scripts/forge/
GATE="$WORK/scripts/forge/gate.sh"

PASS=0; FAIL=0
check() { if eval "$2"; then PASS=$((PASS + 1)); echo "  ok    $1"; else FAIL=$((FAIL + 1)); echo "  FAIL  $1"; fi; }

export FORGE_LOG_DIR="$WORK/logs"

out="$("$GATE" ok -- bash -c 'for i in $(seq 1 100); do echo noise $i; done; echo "Tests: 5 passed"')"; rc=$?
check "success exit code" '[ $rc -eq 0 ]'
check "success prints name=0" 'echo "$out" | grep -q "^ok=0 "'
check "success prints the summary line only" 'echo "$out" | grep -q "5 passed" && ! echo "$out" | grep -q "noise 50"'
check "full output in the log" '[ "$(grep -c noise "$FORGE_LOG_DIR/ok.log")" = 100 ]'

out="$("$GATE" bad -- bash -c 'echo fine; echo "error TS2304: x"; echo more; exit 3')"; rc=$?
check "failure exit code passes through" '[ $rc -eq 3 ]'
check "failure prints error lines" 'echo "$out" | grep -q "error TS2304" && ! echo "$out" | grep -q "^fine"'

out="$("$GATE" quiet -- bash -c 'echo a; echo b; exit 1')"
check "failure without error lines prints the tail" 'echo "$out" | grep -q "^b$"'

check "timing line per gate" '[ "$(wc -l < "$FORGE_LOG_DIR/gate-timing.tsv" | tr -d " ")" = 3 ]'
check "light command not heavy" '[ "$(awk -F"\t" "\$3==\"ok\"{print \$4}" "$FORGE_LOG_DIR/gate-timing.tsv")" = 0 ]'

FORGE_GATE_QOS=none "$GATE" hv -- bash -c 'true # npm run build' >/dev/null
check "build command is heavy" '[ "$(awk -F"\t" "\$3==\"hv\"{print \$4}" "$FORGE_LOG_DIR/gate-timing.tsv")" = 1 ]'
check "slot released after the run" '[ -z "$(ls -A "$(git rev-parse --git-common-dir)/forge-gate-slots" 2>/dev/null)" ]'

FORGE_GATE_HEAVY=0 "$GATE" forced -- bash -c 'true # npm test' >/dev/null
check "heavy override" '[ "$(awk -F"\t" "\$3==\"forced\"{print \$4}" "$FORGE_LOG_DIR/gate-timing.tsv")" = 0 ]'

# two heavy runs with one slot run one after the other
start=$(date +%s)
FORGE_HEAVY_SLOTS=1 FORGE_GATE_QOS=none "$GATE" s1 -- bash -c 'sleep 2 # build' >/dev/null &
sleep 0.5
FORGE_HEAVY_SLOTS=1 FORGE_GATE_QOS=none "$GATE" s2 -- bash -c 'sleep 2 # build' >/dev/null
wait
check "one slot serializes heavy runs" '[ $(( $(date +%s) - start )) -ge 4 ]'

# default log dir is anchored at the project root, not the current directory
mkdir -p sub && (cd sub && unset FORGE_LOG_DIR && "$GATE" sublog -- true >/dev/null)
check "default logs under <project>/.claude/.gate-logs" '[ -f "$WORK/.claude/.gate-logs/sublog.log" ] && [ ! -d "$WORK/sub/.claude" ]'

check "npm run build:prod is heavy" 'FORGE_GATE_QOS=none "$GATE" bp -- bash -c "true # npm run build:prod" >/dev/null; [ "$(awk -F"\t" "\$3==\"bp\"{print \$4}" "$FORGE_LOG_DIR/gate-timing.tsv")" = 1 ]'

# a held slot does not block forever
slots="$(git rev-parse --git-common-dir)/forge-gate-slots"; mkdir -p "$slots/slot.1"; echo $$ > "$slots/slot.1/pid"
start=$(date +%s)
out="$(FORGE_HEAVY_SLOTS=1 FORGE_GATE_MAX_WAIT=1 FORGE_GATE_QOS=none "$GATE" mw -- bash -c 'true # build' 2>&1)"; rc=$?
check "max wait gives up and runs" '[ $rc -eq 0 ] && echo "$out" | grep -q "no free slot" && [ $(( $(date +%s) - start )) -lt 10 ]'
rm -rf "$slots/slot.1"

"$GATE" 2>/dev/null; rc=$?
check "usage error exits 2" '[ $rc -eq 2 ]'

# -C runs inside a directory relative to the project root, whatever the caller's cwd
mkdir -p src/pkg other
out="$(cd other && "$GATE" cdir -C src/pkg -- bash -c 'pwd')"; rc=$?
check "-C runs in <project>/<dir> from another cwd" '[ $rc -eq 0 ] && grep -q "/src/pkg$" "$FORGE_LOG_DIR/cdir.log"'
check "-C run directory in the timing line" '[ "$(awk -F"\t" "\$3==\"cdir\"{print \$2}" "$FORGE_LOG_DIR/gate-timing.tsv")" = "$(cd src/pkg && pwd)" ]'
"$GATE" cabs -C "$WORK/src" -- bash -c 'pwd' >/dev/null
check "-C accepts an absolute directory" 'grep -q "/src$" "$FORGE_LOG_DIR/cabs.log"'
"$GATE" cmiss -C nope -- true 2>/dev/null; rc=$?
check "-C on a missing directory exits 2" '[ $rc -eq 2 ] && [ ! -f "$FORGE_LOG_DIR/cmiss.log" ]'
"$GATE" cbad -C 2>/dev/null; rc=$?
check "-C without a directory is a usage error" '[ $rc -eq 2 ]'
"$GATE" cempty -C "" -- true 2>/dev/null; rc=$?
check "-C with an empty directory is a usage error" '[ $rc -eq 2 ]'
"$GATE" -C src -- true 2>/dev/null; rc=$?
check "a gate name starting with - is a usage error" '[ $rc -eq 2 ]'
"$GATE" nodash true 2>/dev/null; rc=$?
check "missing -- is a usage error" '[ $rc -eq 2 ]'

# FORGE_GATE_SLOT_DIR moves the slots out of the repository
shared="$WORK/shared-slots"
FORGE_GATE_SLOT_DIR="$shared" FORGE_HEAVY_SLOTS=1 FORGE_GATE_QOS=none "$GATE" sd1 -- bash -c 'ls "'"$shared"'" > "'"$WORK"'/held.txt" # build' >/dev/null
check "FORGE_GATE_SLOT_DIR holds the slot during the run" 'grep -q "slot.1" "$WORK/held.txt"'
check "FORGE_GATE_SLOT_DIR slot released" '[ -z "$(ls -A "$shared")" ]'

echo ""; echo "passed: $PASS  failed: $FAIL"; [ "$FAIL" -eq 0 ]
