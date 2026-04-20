#!/usr/bin/env bash
# Render a motion composition with a variant JSON passed as props.
#
# Usage:
#   ./engines/motion/render.sh <variant.json> <composition-id> <out.mp4>
#
# Example:
#   ./engines/motion/render.sh variants/walkthrough-example.json walkthrough outputs/motion/walk.mp4
#
# Composition IDs: ops-console, product-mockup, walkthrough

set -euo pipefail

VARIANT="${1:?variant JSON path required}"
COMPOSITION="${2:?composition id required}"
OUT="${3:?output mp4 path required}"

if [[ ! -f "$VARIANT" ]]; then
  echo "error: variant file not found: $VARIANT" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -d node_modules ]]; then
  echo "[render] installing deps (first run)..."
  npm install --silent
fi

# Strip wrapper fields; pass only the inner variant payload as props
PROPS="$(python3 -c "import json,sys; d=json.load(open('$VARIANT')); print(json.dumps({'variant': d.get('variant', d)}))")"

mkdir -p "$(dirname "$OUT")"

echo "[render] $COMPOSITION -> $OUT"
npx remotion render src/index.ts "$COMPOSITION" "$OUT" --props="$PROPS"
