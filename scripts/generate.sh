#!/bin/bash
# generate.sh — Per-runtime file generator for AIDevTeamForge.
#
# Called by install.sh after structural scaffolding is in place. Iterates
# over registered runtimes and invokes each one's emitter. Emitters read
# src/ (template authoring source) and write runtime-specific files into
# the target project.
#
# Usage: scripts/generate.sh <target-directory>
#
# Extending: drop a new Python file in scripts/emitters/ (e.g. cursor.py),
# add its name to the RUNTIMES list below, and it runs automatically.
# No changes to this orchestrator are required for simple cases.

set -e

TARGET_DIR="${1:-}"
if [ -z "$TARGET_DIR" ]; then
  echo "Usage: $0 <target-dir>" >&2
  exit 1
fi
if [ ! -d "$TARGET_DIR" ]; then
  echo "error: '$TARGET_DIR' is not a directory" >&2
  exit 1
fi

# Resolve the template repo root (generate.sh lives in scripts/ at repo root).
TEMPLATE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_DIR="$TEMPLATE_DIR/src"
EMITTERS_DIR="$TEMPLATE_DIR/scripts/emitters"

if [ ! -d "$SRC_DIR" ]; then
  echo "error: template src/ not found at $SRC_DIR" >&2
  exit 1
fi

# Runtime registry. Override with e.g. RUNTIMES="claude" to emit only one.
# Default: all runtimes with emitters present in scripts/emitters/.
RUNTIMES="${RUNTIMES:-claude codex}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required for runtime emitters" >&2
  exit 1
fi

# ── CoreLLM: generate CLAUDE.md + AGENTS.md from single source ───────────
echo "→ Generating coreLLM files"
python3 "$TEMPLATE_DIR/scripts/generate-corellm.py" \
  --src "$SRC_DIR/files/coreLLM" \
  --out "$TARGET_DIR"

# ── Per-runtime emitters (commands/skills only) ──────────────────────────
for runtime in $RUNTIMES; do
  emitter="$EMITTERS_DIR/${runtime}.py"
  if [ -f "$emitter" ]; then
    echo "→ Emitting for $runtime"
    python3 "$emitter" --src "$SRC_DIR" --target "$TARGET_DIR"
  else
    echo "  (no emitter for $runtime at $emitter, skipping)" >&2
  fi
done
