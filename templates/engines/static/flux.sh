#!/usr/bin/env bash
# Hero image generator via Black Forest Labs Flux API.
#
# Usage:
#   ./engines/static/flux.sh <output_path> <width> <height> [model] <<<"$PROMPT"
# Example:
#   BFL_API_KEY=... ./engines/static/flux.sh assets/heroes/office.png 1024 1024 <<<"a warm editorial office photo"
#
# Env: BFL_API_KEY must be set.

set -euo pipefail

OUT="${1:?output path required}"
WIDTH="${2:-1024}"
HEIGHT="${3:-1024}"
MODEL="${4:-flux-2-max}"
PROMPT="$(cat)"

: "${BFL_API_KEY:?BFL_API_KEY not set}"

mkdir -p "$(dirname "$OUT")"

echo "[flux] submitting $(basename "$OUT") (${WIDTH}x${HEIGHT}, $MODEL)"

payload="$(PROMPT="$PROMPT" WIDTH="$WIDTH" HEIGHT="$HEIGHT" python3 -c 'import json,os; print(json.dumps({"prompt": os.environ["PROMPT"], "width": int(os.environ["WIDTH"]), "height": int(os.environ["HEIGHT"])}))')"

submit_resp="$(curl -sS -X POST "https://api.bfl.ai/v1/$MODEL" \
  -H "Content-Type: application/json" \
  -H "x-key: $BFL_API_KEY" \
  -d "$payload")"

id="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["id"])' <<<"$submit_resp")"
polling_url="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["polling_url"])' <<<"$submit_resp")"

echo "[flux] id=$id"

for i in $(seq 1 60); do
  sleep 2
  poll="$(curl -sS "$polling_url" -H "x-key: $BFL_API_KEY")"
  status="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("status",""))' <<<"$poll")"
  if [[ "$status" == "Ready" ]]; then
    sample_url="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["result"]["sample"])' <<<"$poll")"
    curl -sS "$sample_url" -o "$OUT"
    echo "[flux] saved $OUT"
    exit 0
  fi
  if [[ "$status" == "Error" || "$status" == "Failed" || "$status" == "Request Moderated" || "$status" == "Content Moderated" ]]; then
    echo "[flux] failed ($status): $poll"
    exit 1
  fi
  echo "[flux] status=$status (attempt $i)"
done

echo "[flux] timeout waiting for $id"
exit 1
