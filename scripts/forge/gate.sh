#!/usr/bin/env bash
# Run a quality check with its output kept out of the agent's context.
#
# Usage: scripts/forge/gate.sh <name> -- <command> [args...]
#   e.g. scripts/forge/gate.sh 003-typecheck -- npx tsc --noEmit
#
# Full output goes to $FORGE_LOG_DIR/<name>.log (default .claude/.gate-logs, gitignored).
# Printed: "<name>=<exit> (waited Ns, ran Ns)  (log: <path>)"; on success up to 3 summary lines,
# on failure the first <= 20 error lines (or the last 20 lines when none match).
# Exits with the command's exit code. Read the log further only with a targeted grep.
#
# Heavy commands (builds and test runs) first take one of FORGE_HEAVY_SLOTS machine-wide slots
# (default 2; directories under <git-common-dir>/forge-gate-slots/, shared by every worktree and
# session of the repository; slots of dead processes are reclaimed) and run at lower CPU priority.
#   FORGE_GATE_HEAVY=0|1             override the heavy classification
#   FORGE_GATE_HEAVY_RE=<regex>      override the heavy-command pattern (extended regex)
#   FORGE_HEAVY_SLOTS=<n>            slot count (default 2)
#   FORGE_GATE_QOS=utility|background|none   macOS taskpolicy clamp (default utility; nice -n 10 elsewhere)
# One TSV line per gate is appended to $FORGE_LOG_DIR/gate-timing.tsv:
#   ISO time, tree path, gate name, heavy 0/1, waited s, ran s, exit code.
set -uo pipefail

if [[ $# -lt 3 || "$2" != "--" ]]; then
  echo "usage: scripts/forge/gate.sh <name> -- <command> [args...]" >&2
  exit 2
fi

name="$1"
shift 2
log_dir="${FORGE_LOG_DIR:-.claude/.gate-logs}"
log="$log_dir/$name.log"
mkdir -p "$log_dir"

# --- heavy classification ---------------------------------------------------------------------
cmd_text="$*"
default_heavy_re='(^|[[:space:]:/])(build|test|tests|e2e|test:e2e|playwright|vitest|jest|pytest|tox|nox|bench)([[:space:]]|$)|cargo (build|test)|go (build|test)|gradlew?[[:space:]]|mvn[[:space:]]|xcodebuild|flutter (build|test)|docker (build|compose)'
heavy_re="${FORGE_GATE_HEAVY_RE:-$default_heavy_re}"
if [[ -n "${FORGE_GATE_HEAVY:-}" ]]; then
  heavy="$FORGE_GATE_HEAVY"
elif [[ "$cmd_text" =~ $heavy_re ]]; then
  heavy=1
else
  heavy=0
fi

# --- machine-wide slot semaphore ---------------------------------------------------------------
slot_dir=""
waited=0
release_slot() {
  if [[ -n "$slot_dir" ]]; then
    rm -rf "$slot_dir"
    slot_dir=""
  fi
}
trap release_slot EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# A slot is stale when its owner pid is dead, or when it has no pid file after a 10 s grace.
slot_is_stale() {
  local d="$1" pid age mtime
  if [[ -f "$d/pid" ]]; then
    pid=$(cat "$d/pid" 2>/dev/null || true)
    [[ -z "$pid" ]] && return 0
    kill -0 "$pid" 2>/dev/null && return 1
    return 0
  fi
  mtime=$(stat -f %m "$d" 2>/dev/null || stat -c %Y "$d" 2>/dev/null || date +%s)
  age=$(( $(date +%s) - mtime ))
  [[ $age -gt 10 ]]
}

acquire_slot() {
  local root="$1" n="$2" i d
  mkdir -p "$root"
  for ((i = 1; i <= n; i++)); do
    d="$root/slot.$i"
    if mkdir "$d" 2>/dev/null; then
      echo $$ >"$d/pid"
      slot_dir="$d"
      return 0
    fi
    if slot_is_stale "$d"; then
      rm -rf "$d"
      if mkdir "$d" 2>/dev/null; then
        echo $$ >"$d/pid"
        slot_dir="$d"
        return 0
      fi
    fi
  done
  return 1
}

if [[ "$heavy" == "1" ]]; then
  common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)
  if [[ -n "$common" ]]; then
    slots="${FORGE_HEAVY_SLOTS:-2}"
    [[ "$slots" =~ ^[1-9][0-9]*$ ]] || slots=2
    wait_start=$(date +%s)
    until acquire_slot "$common/forge-gate-slots" "$slots"; do
      sleep 3
    done
    waited=$(( $(date +%s) - wait_start ))
  fi
fi

# --- run with lower priority for heavy commands ------------------------------------------------
qos="${FORGE_GATE_QOS:-utility}"
prefix=()
if [[ "$heavy" == "1" && "$qos" != "none" ]]; then
  if command -v taskpolicy >/dev/null 2>&1; then
    prefix=(taskpolicy -c "$qos")
  else
    prefix=(nice -n 10)
  fi
fi

run_start=$(date +%s)
"${prefix[@]+"${prefix[@]}"}" "$@" >"$log" 2>&1
code=$?
ran=$(( $(date +%s) - run_start ))
release_slot

printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$PWD" "$name" "$heavy" "$waited" "$ran" "$code" \
  >>"$log_dir/gate-timing.tsv"

echo "$name=$code (waited ${waited}s, ran ${ran}s)  (log: $log)"
if [[ $code -eq 0 ]]; then
  tail -n 40 "$log" \
    | grep -E -i '(passed|failed|skipped|successful|total|tests?[: ]|errors?|warnings?|problems?)' \
    | tail -n 3 | cut -c1-200
else
  matches=$(grep -E -i -m 20 '(error|fail|✘|✗|×|ERR!|not ok|panic)' "$log" | cut -c1-200)
  if [[ -n "$matches" ]]; then
    echo "$matches"
  else
    tail -n 20 "$log" | cut -c1-200
  fi
fi
exit $code
