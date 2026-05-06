#!/usr/bin/env bash
# Extract every Vue SFC  into compiled TS,
# placed under the framework's extracted-vue for downstream graph indexing.
#
# Usage:
#   scripts/vue-to-ts.sh                       # default target + output
#   scripts/vue-to-ts --include-template    # passthrough flags
#   VUE_TO_TS_TARGET=/other/repo scripts/vue-to-ts.sh
#   VUE_TO_TS_OUT=/tmp/out      scripts/vue-to-ts.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOL_DIR="$REPO_ROOT/tools/vue-to-ts"
TOOL_ENTRY="$TOOL_DIR/index.mjs"

DEFAULT_TARGET="$REPO_ROOT/src"
DEFAULT_OUT="$REPO_ROOT/extracted-vue"

TARGET="${VUE_TO_TS_TARGET:-$DEFAULT_TARGET}"
OUT_DIR="${VUE_TO_TS_OUT:-$DEFAULT_OUT}"

if [ ! -f "$TOOL_ENTRY" ]; then
  echo "error: tool entry not found at $TOOL_ENTRY" >&2
  exit 2
fi

if [ ! -d "$TARGET" ]; then
  echo "error: target directory not found: $TARGET" >&2
  echo "       set VUE_TO_TS_TARGET to override" >&2
  exit 2
fi

if [ ! -d "$TOOL_DIR/node_modules" ]; then
  echo "vue-to-ts dependencies not installed; running npm install..."
  ( cd "$TOOL_DIR" && npm install --silent )
fi

mkdir -p "$OUT_DIR"

echo "vue-to-ts"
echo "  target: $TARGET"
echo "  out:    $OUT_DIR"
echo "  flags:  $*"
echo

START_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
node "$TOOL_ENTRY" "$TARGET" --mode mirror --out "$OUT_DIR" "$@"
END_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

VUE_COUNT="$(find "$TARGET" -name '*.vue' \
  -not -path '*/node_modules/*' \
  -not -path '*/dist/*' \
  -not -path '*/.git/*' \
  -not -path '*/.cache/*' \
  -not -path '*/.turbo/*' \
  -not -path '*/coverage/*' \
  | wc -l | tr -d ' ')"

OUT_COUNT="$(find "$OUT_DIR" \( -name '*.vue.ts' -o -name '*.vue.js' \) | wc -l | tr -d ' ')"

cat > "$OUT_DIR/.manifest.json" <<EOF
{
  "tool": "vue-to-ts",
  "target": "$TARGET",
  "out_dir": "$OUT_DIR",
  "started_at": "$START_TS",
  "completed_at": "$END_TS",
  "source_vue_count": $VUE_COUNT,
  "output_count": $OUT_COUNT,
  "flags": "$*"
}
EOF

echo
echo "manifest: $OUT_DIR/.manifest.json"
echo "source .vue files: $VUE_COUNT"
echo "output files:      $OUT_COUNT"
