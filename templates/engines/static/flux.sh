#!/usr/bin/env bash
# Backcompat wrapper around generate_hero.py.
#
# Historical signature kept for variants / skills that call flux.sh directly:
#   ./engines/static/flux.sh <output_path> <width> <height> [model] <<<"$PROMPT"
#
# New code should call generate_hero.py. flux.sh just forwards the request with
# IMAGE_PROVIDER=bfl pinned, so nothing downstream of BFL-specific callers breaks.

set -euo pipefail

OUT="${1:?output path required}"
WIDTH="${2:-1024}"
HEIGHT="${3:-1024}"
MODEL_ARG="${4:-}"

if [[ -n "$MODEL_ARG" ]]; then
  export BFL_MODEL="$MODEL_ARG"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE_PROVIDER=bfl exec python3 "$SCRIPT_DIR/generate_hero.py" "$OUT" "$WIDTH" "$HEIGHT"
