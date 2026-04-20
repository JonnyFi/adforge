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

VARIANT_ARG="${1:?variant JSON path required}"
COMPOSITION="${2:?composition id required}"
OUT_ARG="${3:?output mp4 path required}"

if [[ ! -f "$VARIANT_ARG" ]]; then
  echo "error: variant file not found: $VARIANT_ARG" >&2
  exit 1
fi

# Resolve to absolute paths before cd'ing to the engine dir.
VARIANT="$(cd "$(dirname "$VARIANT_ARG")" && pwd)/$(basename "$VARIANT_ARG")"
mkdir -p "$(dirname "$OUT_ARG")"
OUT="$(cd "$(dirname "$OUT_ARG")" && pwd)/$(basename "$OUT_ARG")"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -d node_modules ]]; then
  echo "[render] installing deps (first run)..."
  npm install --silent
fi

# Expose project-root assets/ under public/assets/ so brand.chrome path
# references resolve the same in static (PIL) and motion (Remotion).
if [[ -d "$PROJECT_ROOT/assets" ]]; then
  mkdir -p public
  rm -rf public/assets
  cp -R "$PROJECT_ROOT/assets" public/assets
fi

# Expose project-root fonts/ under public/fonts/ so brand.ts @font-face
# declarations (staticFile("fonts/<name>.ttf")) resolve during render.
if [[ -d "$PROJECT_ROOT/fonts" ]]; then
  mkdir -p public
  rm -rf public/fonts
  cp -R "$PROJECT_ROOT/fonts" public/fonts
fi

# Strip wrapper fields; pass only the inner variant payload as props
PROPS="$(python3 -c "import json,sys; d=json.load(open('$VARIANT')); print(json.dumps({'variant': d.get('variant', d)}))")"

echo "[render] $COMPOSITION -> $OUT"
npx remotion render src/index.ts "$COMPOSITION" "$OUT" --props="$PROPS"
