#!/usr/bin/env bash
# adforge internal test harness.
#
# Simulates a new user going through the happy path:
#   1. scaffold a project (npx adforge init)
#   2. fetch open-source fonts the default brand.json points at
#   3. render a static advertorial PNG from the example variant
#   4. render a motion ops-console MP4 from the example variant (optional; slow)
#
# Usage:
#   ./test/run-tests.sh                # all tests
#   ./test/run-tests.sh --skip-motion  # skip the slow Remotion test
#   ./test/run-tests.sh --keep         # don't wipe /tmp/adforge-tests at start

set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORK=/tmp/adforge-tests
SKIP_MOTION=0
KEEP=0

for arg in "$@"; do
  case "$arg" in
    --skip-motion) SKIP_MOTION=1 ;;
    --keep) KEEP=1 ;;
    *) echo "unknown arg: $arg"; exit 2 ;;
  esac
done

PASS=0
FAIL=0
FAILED_TESTS=()

pass() { echo "  [PASS] $1"; PASS=$((PASS+1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); FAILED_TESTS+=("$1"); }
head() { echo; echo "=== $1 ==="; }

if [ $KEEP -eq 0 ]; then
  rm -rf "$WORK"
fi
mkdir -p "$WORK"

# ---------------------------------------------------------------------------
# Test 1 — scaffold
# ---------------------------------------------------------------------------
head "Test 1: scaffold"

PROJECT="$WORK/demo"
rm -rf "$PROJECT"

if node "$REPO/bin/adforge.js" init "$PROJECT" > "$WORK/init.log" 2>&1; then
  pass "init succeeded"
else
  fail "init exit code"
  cat "$WORK/init.log"
fi

# File-structure checks. Each expected path must exist after scaffold.
expected=(
  "adforge.config.json"
  "brand.json"
  ".env.example"
  ".gitignore"
  "AGENTS.md"
  "README.md"
  "variants/example.json"
  "variants/ops-console-example.json"
  "engines/static/compose.py"
  "engines/static/flux.sh"
  "engines/static/requirements.txt"
  "engines/motion/package.json"
  "engines/motion/src/Root.tsx"
  "engines/motion/src/engines/OpsConsole.tsx"
  "engines/motion/src/engines/ProductMockup.tsx"
  "engines/motion/src/engines/Walkthrough.tsx"
  "engines/motion/render.sh"
  "adapters/meta/deploy.py"
  "adapters/meta/review.py"
  "adapters/meta/actions.py"
  ".claude/skills/adforge/SKILL.md"
  ".claude/skills/new-campaign/SKILL.md"
  ".claude/skills/add-creative/SKILL.md"
  ".claude/skills/review-performance/SKILL.md"
  ".claude/skills/setup/SKILL.md"
  ".claude/skills/creative-director/SKILL.md"
  ".claude/skills/composer-speccer/SKILL.md"
  ".claude/skills/performance-analyst/SKILL.md"
  ".claude/commands/adforge.md"
)

missing=0
for rel in "${expected[@]}"; do
  if [ ! -e "$PROJECT/$rel" ]; then
    echo "    missing: $rel"
    missing=$((missing+1))
  fi
done

if [ $missing -eq 0 ]; then
  pass "all ${#expected[@]} expected files present"
else
  fail "$missing expected files missing"
fi

# Doctor should run (exit code may be non-zero if ffmpeg is missing — not fatal).
if node "$REPO/bin/adforge.js" doctor > "$WORK/doctor.log" 2>&1; then
  pass "doctor exited 0"
else
  echo "    (doctor exited non-zero — usually means ffmpeg missing; not fatal)"
  pass "doctor ran (non-zero exit tolerated)"
fi

# ---------------------------------------------------------------------------
# Test 2 — static compose (advertorial example, 4x5)
# ---------------------------------------------------------------------------
head "Test 2: static compose"

FONTS="$PROJECT/fonts"
mkdir -p "$FONTS"

fetch_font() {
  local url="$1"
  local dest="$2"
  if [ -f "$dest" ]; then return 0; fi
  if command -v curl > /dev/null; then
    curl -fsSL "$url" -o "$dest"
  else
    wget -q "$url" -O "$dest"
  fi
}

# Google Fonts static TTFs (the same files brand.json defaults expect by name).
echo "  fetching open-source fonts (Instrument Serif, JetBrains Mono, Inter)..."
set -e
fetch_font "https://github.com/google/fonts/raw/main/ofl/instrumentserif/InstrumentSerif-Regular.ttf" \
           "$FONTS/InstrumentSerif-Regular.ttf"
fetch_font "https://github.com/google/fonts/raw/main/ofl/instrumentserif/InstrumentSerif-Italic.ttf" \
           "$FONTS/InstrumentSerif-Italic.ttf"
fetch_font "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Medium.ttf" \
           "$FONTS/JetBrainsMono-Medium.ttf"
# Inter is only distributed as a variable TTF on google/fonts now. PIL renders it
# at the default instance (regular-ish). For tests that's enough; real projects
# should drop proper static TTFs into fonts/ per brand.json.
INTER_VF_URL="https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf"
fetch_font "$INTER_VF_URL" "$FONTS/Inter-Regular.ttf"
cp "$FONTS/Inter-Regular.ttf" "$FONTS/Inter-Medium.ttf"
cp "$FONTS/Inter-Regular.ttf" "$FONTS/Inter-SemiBold.ttf"
set +e

pass "fonts fetched"

# Install Pillow into an isolated venv to avoid polluting user python.
VENV="$WORK/venv"
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV" || { fail "venv create"; exit 1; }
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --quiet -r "$PROJECT/engines/static/requirements.txt" || { fail "pip install"; exit 1; }
pass "pillow installed"

OUT_PNG="$PROJECT/outputs/static/example_4x5.png"
mkdir -p "$(dirname "$OUT_PNG")"
if python3 "$PROJECT/engines/static/compose.py" \
     "$PROJECT/variants/example.json" 4x5 "$OUT_PNG" > "$WORK/compose.log" 2>&1; then
  pass "compose exited 0"
else
  fail "compose exit code"
  tail -40 "$WORK/compose.log"
fi

if [ -f "$OUT_PNG" ]; then
  size=$(wc -c < "$OUT_PNG" | tr -d ' ')
  if [ "$size" -gt 20000 ]; then
    pass "output PNG exists (${size} bytes)"
  else
    fail "PNG too small (${size} bytes) — likely blank"
  fi
else
  fail "no PNG produced"
fi

deactivate

# ---------------------------------------------------------------------------
# Test 3 — motion render (ops-console example)
# ---------------------------------------------------------------------------
if [ $SKIP_MOTION -eq 1 ]; then
  head "Test 3: motion render (SKIPPED)"
else
  head "Test 3: motion render"

  MOTION="$PROJECT/engines/motion"

  echo "  installing Remotion deps (one-time, ~60–120s)..."
  if (cd "$MOTION" && npm install --silent > "$WORK/npm-install.log" 2>&1); then
    pass "npm install"
  else
    fail "npm install"
    tail -30 "$WORK/npm-install.log"
  fi

  OUT_MP4="$PROJECT/outputs/motion/ops-test.mp4"
  mkdir -p "$(dirname "$OUT_MP4")"

  echo "  rendering ops-console (this can take a minute)..."
  if (cd "$MOTION" && bash render.sh "$PROJECT/variants/ops-console-example.json" \
       ops-console "$OUT_MP4" > "$WORK/render.log" 2>&1); then
    pass "render.sh exited 0"
  else
    fail "render.sh exit code"
    tail -60 "$WORK/render.log"
  fi

  if [ -f "$OUT_MP4" ]; then
    size=$(wc -c < "$OUT_MP4" | tr -d ' ')
    if [ "$size" -gt 50000 ]; then
      pass "output MP4 exists (${size} bytes)"
    else
      fail "MP4 too small (${size} bytes)"
    fi
  else
    fail "no MP4 produced"
  fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
head "Summary"
echo "  passed: $PASS"
echo "  failed: $FAIL"
if [ $FAIL -gt 0 ]; then
  echo "  failed tests:"
  for t in "${FAILED_TESTS[@]}"; do echo "    - $t"; done
fi
echo
echo "  artifacts in: $WORK"
[ -f "$PROJECT/outputs/static/example_4x5.png" ] && echo "    static: $PROJECT/outputs/static/example_4x5.png"
[ -f "$PROJECT/outputs/motion/ops-test.mp4" ] && echo "    motion: $PROJECT/outputs/motion/ops-test.mp4"

exit $FAIL
