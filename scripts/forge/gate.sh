#!/usr/bin/env bash
# Run a quality check with its output kept out of the agent's context.
#
# Usage: scripts/forge/gate.sh <name> [-C <dir>] -- <command> [args...]
#   e.g. scripts/forge/gate.sh 003-typecheck -- npx tsc --noEmit
#        scripts/forge/gate.sh 003-lint -C app/packages/web -- npx eslint src
#
# -C runs the command inside <dir>: relative to <project> (the directory that holds scripts/forge/), never to
# the caller's cwd, so a wrapper project runs checks in its source repo whatever directory the session is in.
#
# Full output goes to $FORGE_LOG_DIR/<name>.log (default <project>/.claude/.gate-logs, gitignored;
# <project> is the directory that holds scripts/forge/, so logs stay out of a wrapped source repo).
# Printed: "<name>=<exit> (waited Ns, ran Ns)  (log: <path>)"; on success up to 3 summary lines,
# on failure the first <= 20 error lines (or the last 20 lines when none match).
# Exits with the command's exit code. Read the log further only with a targeted grep.
#
# Heavy commands (builds and test runs) first take one of FORGE_HEAVY_SLOTS machine-wide slots
# (default 2; directories under <git-common-dir>/forge-gate-slots/, shared by every worktree and
# session of the repository; slots of dead processes are reclaimed) and run at lower CPU priority.
#   FORGE_GATE_SLOT_DIR=<dir>        share the slots through <dir> instead (e.g. ~/.cache/forge-gate-slots for
#                                    several clones or projects building on one machine)
#   FORGE_GATE_HEAVY=0|1             override the heavy classification
#   FORGE_GATE_HEAVY_RE=<regex>      override the heavy-command pattern (extended regex)
#   FORGE_HEAVY_SLOTS=<n>            slot count (default 2)
#   FORGE_GATE_MAX_WAIT=<s>          give up waiting for a slot after s seconds and run anyway (default 1800)
#   FORGE_GATE_QOS=utility|background|none   macOS taskpolicy clamp (default utility; nice -n 10 elsewhere)
# One TSV line per gate is appended to $FORGE_LOG_DIR/gate-timing.tsv:
#   ISO time, run directory, gate name, heavy 0/1, waited s, ran s, exit code.
set -uo pipefail

usage() {
  echo "usage: scripts/forge/gate.sh <name> [-C <dir>] -- <command> [args...]" >&2
  exit 2
}

[[ $# -ge 1 && -n "$1" && "$1" != -* ]] || usage
name="$1"
shift
project_root="$(cd "$(dirname "$0")/../.." && pwd)"
run_dir="$PWD"
if [[ "${1:-}" == "-C" ]]; then
  [[ $# -ge 2 && -n "$2" ]] || usage
  case "$2" in
    /*) run_dir="$2" ;;
    *) run_dir="$project_root/$2" ;;
  esac
  if [[ ! -d "$run_dir" ]]; then
    echo "gate.sh: -C $2: no such directory ($run_dir)" >&2
    exit 2
  fi
  run_dir="$(cd "$run_dir" && pwd)"
  shift 2
fi
[[ $# -ge 2 && "$1" == "--" ]] || usage
shift
log_dir="${FORGE_LOG_DIR:-$project_root/.claude/.gate-logs}"
log="$log_dir/$name.log"
mkdir -p "$log_dir"

# --- heavy classification ---------------------------------------------------------------------
cmd_text="$*"
default_heavy_re='(^|[[:space:]:/])(build|test|tests|e2e|playwright|vitest|jest|pytest|tox|nox|bench)([-:][^[:space:]]+)?([[:space:]]|$)|emulators:(exec|start)|cargo (build|test)|go (build|test)|gradlew?[[:space:]]|mvnw?[[:space:]]|xcodebuild|flutter (build|test)|docker (build|compose)'
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
  slot_root="${FORGE_GATE_SLOT_DIR:-}"
  if [[ -z "$slot_root" ]]; then
    # Plain --git-common-dir works on every git version; make it absolute ourselves.
    common=$(cd "$project_root" && git rev-parse --git-common-dir 2>/dev/null || true)
    if [[ -n "$common" && "$common" != /* ]]; then
      common="$project_root/$common"
    fi
    [[ -n "$common" && -d "$common" ]] && slot_root="$common/forge-gate-slots"
  fi
  if [[ -n "$slot_root" ]]; then
    slots="${FORGE_HEAVY_SLOTS:-2}"
    [[ "$slots" =~ ^[1-9][0-9]*$ ]] || slots=2
    max_wait="${FORGE_GATE_MAX_WAIT:-1800}"
    [[ "$max_wait" =~ ^[0-9]+$ ]] || max_wait=1800
    wait_start=$(date +%s)
    until acquire_slot "$slot_root" "$slots"; do
      if (( $(date +%s) - wait_start >= max_wait )); then
        echo "gate.sh: no free slot after ${max_wait}s; running without one" >&2
        break
      fi
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
(cd "$run_dir" && "${prefix[@]+"${prefix[@]}"}" "$@") >"$log" 2>&1
code=$?
ran=$(( $(date +%s) - run_start ))
release_slot

printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$run_dir" "$name" "$heavy" "$waited" "$ran" "$code" \
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
