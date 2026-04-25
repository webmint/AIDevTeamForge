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

# Resolve a Python 3 interpreter. Same selector as install.sh and the wizard
# launcher: prefer python3, fall back to Windows py launcher, then bare python
# if it reports 3.x.
if command -v python3 >/dev/null 2>&1; then
  PYTHON3="python3"
elif command -v py >/dev/null 2>&1; then
  PYTHON3="py -3"
elif command -v python >/dev/null 2>&1 && [ "$(python -c 'import sys; print(sys.version_info[0])' 2>/dev/null)" = "3" ]; then
  PYTHON3="python"
else
  echo "error: Python 3 not found (tried python3, py -3, python). Install Python 3.8+ and re-run." >&2
  exit 1
fi

# ── CoreLLM: generate CLAUDE.md + AGENTS.md from single source ───────────
# Forward RUNTIMES filter so a single-runtime install doesn't produce the
# other runtime's CLAUDE.md / AGENTS.md file.
echo "→ Generating coreLLM files"
$PYTHON3 "$TEMPLATE_DIR/scripts/generate-corellm.py" \
  --src "$SRC_DIR/files/coreLLM" \
  --out "$TARGET_DIR" \
  --runtimes "$RUNTIMES"

# ── Agents: generate per-runtime agent files from universal sources ──────
echo "→ Generating agents"
$PYTHON3 "$TEMPLATE_DIR/scripts/generate-agents.py" \
  --src "$SRC_DIR/agents" \
  --target "$TARGET_DIR" \
  --runtimes "$RUNTIMES"

# ── Per-runtime emitters (commands/skills only) ──────────────────────────
for runtime in $RUNTIMES; do
  emitter="$EMITTERS_DIR/${runtime}.py"
  if [ -f "$emitter" ]; then
    echo "→ Emitting for $runtime"
    $PYTHON3 "$emitter" --src "$SRC_DIR" --target "$TARGET_DIR"
  else
    echo "  (no emitter for $runtime at $emitter, skipping)" >&2
  fi
done
