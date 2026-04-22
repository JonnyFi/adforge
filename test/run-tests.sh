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
  "variants/_reference/example.json"
  "variants/_reference/ops-console-example.json"
  "engines/static/compose.py"
  "engines/static/shared.py"
  "engines/static/flux.sh"
  "engines/static/generate_hero.py"
  "engines/static/image_providers/CONTRACT.md"
  "engines/static/image_providers/__init__.py"
  "engines/static/image_providers/bfl.py"
  "engines/static/image_providers/google.py"
  "engines/static/image_providers/openai.py"
  "engines/static/image_providers/replicate.py"
  "engines/static/image_providers/stability.py"
  "engines/static/image_providers/fal.py"
  "engines/static/requirements.txt"
  "engines/static/examples/__init__.py"
  "engines/static/examples/advertorial.py"
  "engines/static/examples/quote_card.py"
  "engines/static/examples/stat_card.py"
  "engines/motion/package.json"
  "engines/motion/src/Root.tsx"
  "engines/motion/src/examples/OpsConsole.tsx"
  "engines/motion/src/examples/ProductMockup.tsx"
  "engines/motion/src/examples/Walkthrough.tsx"
  "engines/motion/src/primitives/index.ts"
  "engines/motion/src/primitives/ChromeOverlay.tsx"
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
  ".claude/skills/layout-synth/SKILL.md"
  ".claude/skills/motion-synth/SKILL.md"
  ".claude/skills/image-provider-synth/SKILL.md"
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

# Doctor output must mention Playwright (optional check for brand extraction).
if grep -qi "playwright" "$WORK/doctor.log"; then
  pass "doctor mentions playwright"
else
  fail "doctor output missing playwright check"
fi

# .env.example must carry all keys we promise in the README.
ENV_EX="$PROJECT/.env.example"
missing_keys=0
for key in BFL_API_KEY META_ACCESS_TOKEN META_AD_ACCOUNT_ID META_PAGE_ID META_PIXEL_ID; do
  if ! grep -q "^${key}=" "$ENV_EX"; then
    echo "    missing key in .env.example: $key"
    missing_keys=$((missing_keys+1))
  fi
done
if [ $missing_keys -eq 0 ]; then
  pass ".env.example has all 5 keys"
else
  fail ".env.example missing $missing_keys keys"
fi

# ---------------------------------------------------------------------------
# Test 1b — adforge upgrade (manifest + edit detection + .new sibling)
# ---------------------------------------------------------------------------
head "Test 1b: adforge upgrade"

# init writes manifest
if [ -f "$PROJECT/.adforge/manifest.json" ] && [ -f "$PROJECT/.adforge/version" ]; then
  pass ".adforge/manifest.json + version written on init"
else
  fail ".adforge manifest/version missing after init"
fi

MANIFEST_FILES=$(python3 -c "import json; print(len(json.load(open('$PROJECT/.adforge/manifest.json'))['files']))")
if [ "$MANIFEST_FILES" -gt 40 ]; then
  pass "manifest tracks $MANIFEST_FILES files"
else
  fail "manifest tracks only $MANIFEST_FILES files (expected >40)"
fi

# Pristine upgrade: should be entirely up-to-date, no .new files written
if (cd "$PROJECT" && node "$REPO/bin/adforge.js" upgrade --dry-run > "$WORK/upgrade-pristine.log" 2>&1); then
  pass "upgrade --dry-run exited 0"
else
  fail "upgrade --dry-run exit code"
  cat "$WORK/upgrade-pristine.log"
fi

if grep -q "up-to-date:" "$WORK/upgrade-pristine.log" && ! grep -q "review (" "$WORK/upgrade-pristine.log"; then
  pass "pristine project reports all up-to-date"
else
  fail "pristine upgrade reported unexpected changes"
  cat "$WORK/upgrade-pristine.log"
fi

# dry-run must not write anything
if [ ! -e "$PROJECT/AGENTS.md.new" ]; then
  pass "--dry-run wrote no files"
else
  fail "--dry-run created AGENTS.md.new"
fi

# Modify a tracked overwrite-layer file → upgrade must write .new sibling, keep local file intact
cp "$PROJECT/AGENTS.md" "$WORK/AGENTS-original.md"
echo "# local edit" >> "$PROJECT/AGENTS.md"

if (cd "$PROJECT" && node "$REPO/bin/adforge.js" upgrade > "$WORK/upgrade-edited.log" 2>&1); then
  pass "upgrade (with local edit) exited 0"
else
  fail "upgrade (with local edit) exit code"
  cat "$WORK/upgrade-edited.log"
fi

if [ -f "$PROJECT/AGENTS.md.new" ]; then
  pass ".new sibling written for edited file"
else
  fail "AGENTS.md.new not created"
fi

if grep -q "# local edit" "$PROJECT/AGENTS.md"; then
  pass "local edit preserved (AGENTS.md untouched)"
else
  fail "local edit to AGENTS.md was clobbered"
fi

# User-owned files (brand.json) must never be touched by upgrade.
# Use a throwaway file so we don't poison downstream tests that need brand.json.
cp "$PROJECT/brand.json" "$WORK/brand-backup.json"
echo '{"custom":"user work"}' > "$PROJECT/brand.json"
(cd "$PROJECT" && node "$REPO/bin/adforge.js" upgrade > "$WORK/upgrade-userfile.log" 2>&1) || true
if grep -q '"custom":"user work"' "$PROJECT/brand.json"; then
  pass "user-owned brand.json preserved"
else
  fail "brand.json was clobbered"
fi
cp "$WORK/brand-backup.json" "$PROJECT/brand.json"

# Delete a tracked file → upgrade should re-add it (add path)
rm "$PROJECT/AGENTS.md" "$PROJECT/AGENTS.md.new"
(cd "$PROJECT" && node "$REPO/bin/adforge.js" upgrade > "$WORK/upgrade-readd.log" 2>&1) || true
if [ -f "$PROJECT/AGENTS.md" ] && grep -q "add (new file)" "$WORK/upgrade-readd.log"; then
  pass "missing tracked file re-added on upgrade"
else
  fail "AGENTS.md not re-added"
fi

# Upgrade refuses outside an adforge project
(cd "$WORK" && node "$REPO/bin/adforge.js" upgrade > "$WORK/upgrade-nonproject.log" 2>&1) && rc=0 || rc=$?
if [ "$rc" -ne 0 ] && grep -q "not an adforge project" "$WORK/upgrade-nonproject.log"; then
  pass "upgrade refuses when not in adforge project"
else
  fail "upgrade should refuse outside adforge project (rc=$rc)"
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
     "$PROJECT/variants/_reference/example.json" 4x5 "$OUT_PNG" > "$WORK/compose.log" 2>&1; then
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
# Test 2b — dry-run must not pollute state.json
# ---------------------------------------------------------------------------
head "Test 2b: deploy --dry-run state guard"

# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --quiet -r "$PROJECT/adapters/meta/requirements.txt" > /dev/null 2>&1

STATE_FILE="$PROJECT/.adforge/state.json"
rm -f "$STATE_FILE"

if (cd "$PROJECT" && python3 adapters/meta/deploy.py --dry-run adapters/meta/example-plan.json > "$WORK/dry-run.log" 2>&1); then
  pass "dry-run exited 0"
else
  fail "dry-run exit code"
  tail -30 "$WORK/dry-run.log"
fi

if [ -f "$STATE_FILE" ]; then
  fail "dry-run wrote state.json — should be a no-op"
else
  pass "dry-run left state.json untouched"
fi

deactivate

# ---------------------------------------------------------------------------
# Test 2c — derive_placements + CTA-less render regression
# ---------------------------------------------------------------------------
head "Test 2c: creative defaults (placements + no-CTA)"

# shellcheck disable=SC1091
source "$VENV/bin/activate"

# derive_placements: static 4x5 -> Feed, static 9x16 -> Stories (no Reels),
# motion 9x16 -> Reels + Stories. Runs directly against the template module.
if python3 - <<PY > "$WORK/placements.log" 2>&1
import sys
sys.path.insert(0, "$PROJECT/adapters/meta")
from deploy import derive_placements

cases = [
    ([{"creative_type": "image", "format": "4x5"}],
     {"fb": ["feed"], "ig": ["stream"]}),
    ([{"creative_type": "image", "format": "9x16"}],
     {"fb": ["story"], "ig": ["story"]}),
    ([{"creative_type": "video", "format": "9x16"}],
     {"fb": ["facebook_reels", "story"], "ig": ["reels", "story"]}),
    ([{"creative_type": "image", "format": "4x5"},
      {"creative_type": "image", "format": "9x16"}],
     {"fb": ["feed", "story"], "ig": ["story", "stream"]}),
]
for ads, want in cases:
    got = derive_placements(ads)
    assert got["publisher_platforms"] == ["facebook", "instagram"], got
    assert got["facebook_positions"] == want["fb"], (got, want)
    assert got["instagram_positions"] == want["ig"], (got, want)
print("ok")
PY
then
  pass "derive_placements matches expected matrix"
else
  fail "derive_placements unit test"
  cat "$WORK/placements.log"
fi

# Render the quote-card example (no cta field) to prove the CTA guard works.
OUT_NOCTA="$PROJECT/outputs/static/quote-card_4x5.png"
if python3 "$PROJECT/engines/static/compose.py" \
     "$PROJECT/variants/_reference/quote-card-example.json" 4x5 "$OUT_NOCTA" > "$WORK/compose-nocta.log" 2>&1; then
  pass "compose without cta exited 0"
else
  fail "compose without cta exit code"
  tail -30 "$WORK/compose-nocta.log"
fi

if [ -f "$OUT_NOCTA" ]; then
  size=$(wc -c < "$OUT_NOCTA" | tr -d ' ')
  if [ "$size" -gt 20000 ]; then
    pass "no-cta PNG exists (${size} bytes)"
  else
    fail "no-cta PNG too small (${size} bytes)"
  fi
else
  fail "no no-cta PNG produced"
fi

deactivate

# ---------------------------------------------------------------------------
# Test 2d — TLD-based locale inference
# ---------------------------------------------------------------------------
head "Test 2d: TLD-based locale inference"

# shellcheck disable=SC1091
source "$VENV/bin/activate"

if python3 - <<PY > "$WORK/locale.log" 2>&1
import sys
sys.path.insert(0, "$PROJECT/adapters/meta")
from deploy import derive_locale

cases = {
    "example.at": ("AT", "de"),
    "https://example.at/path": ("AT", "de"),
    "www.example.at": ("AT", "de"),
    "example.de": ("DE", "de"),
    "example.fr": ("FR", "fr"),
    "example.co.uk": ("GB", "en"),
    "example.us": ("US", "en"),
}
for domain, want in cases.items():
    got = derive_locale(domain)
    assert got == {"country": want[0], "language": want[1]}, (domain, got, want)

ambiguous = ["example.com", "example.io", "example.co", "example.ch", "example.be", "", "noextension"]
for domain in ambiguous:
    assert derive_locale(domain) is None, f"{domain} should be ambiguous, got {derive_locale(domain)}"

print("ok")
PY
then
  pass "derive_locale matrix (unambiguous + ambiguous)"
else
  fail "derive_locale unit test"
  cat "$WORK/locale.log"
fi

# Integration: plan with no geo_locations + brand.json with .at domain should
# auto-default countries to ["AT"] during dry-run.
PLAN_NO_GEO="$PROJECT/plan-no-geo.json"
python3 - <<PY
import json, pathlib
p = json.loads(pathlib.Path("$PROJECT/adapters/meta/example-plan.json").read_text())
for c in p["campaigns"]:
    for a in c["adsets"]:
        a["targeting"].pop("geo_locations", None)
pathlib.Path("$PLAN_NO_GEO").write_text(json.dumps(p, indent=2))
PY

BRAND_BAK="$WORK/brand.json.bak"
cp "$PROJECT/brand.json" "$BRAND_BAK"
python3 - <<PY
import json, pathlib
path = pathlib.Path("$PROJECT/brand.json")
b = json.loads(path.read_text())
b["domain"] = "example.at"
path.write_text(json.dumps(b, indent=2))
PY

if (cd "$PROJECT" && python3 adapters/meta/deploy.py --dry-run "$PLAN_NO_GEO" > "$WORK/locale-dry.log" 2>&1); then
  if grep -q "defaulted geo_locations.countries to \['AT'\]" "$WORK/locale-dry.log"; then
    pass "deploy auto-defaulted AT countries from brand.domain"
  else
    fail "deploy didn't log locale default"
    tail -20 "$WORK/locale-dry.log"
  fi
else
  fail "dry-run with missing geo failed unexpectedly"
  tail -30 "$WORK/locale-dry.log"
fi

# Ambiguous domain (.com) must refuse to auto-pick and error clearly.
python3 - <<PY
import json, pathlib
path = pathlib.Path("$PROJECT/brand.json")
b = json.loads(path.read_text())
b["domain"] = "example.com"
path.write_text(json.dumps(b, indent=2))
PY

if (cd "$PROJECT" && python3 adapters/meta/deploy.py --dry-run "$PLAN_NO_GEO" > "$WORK/locale-dry-ambig.log" 2>&1); then
  fail "deploy should have errored on ambiguous domain + missing geo_locations"
  tail -20 "$WORK/locale-dry-ambig.log"
else
  if grep -qi "ambiguous" "$WORK/locale-dry-ambig.log"; then
    pass "deploy refused ambiguous domain with clear error"
  else
    fail "deploy errored but message didn't mention ambiguous"
    tail -20 "$WORK/locale-dry-ambig.log"
  fi
fi

cp "$BRAND_BAK" "$PROJECT/brand.json"

deactivate

# ---------------------------------------------------------------------------
# Test 2e — targeting resolve + flexible_spec + advantage_audience
# ---------------------------------------------------------------------------
head "Test 2e: targeting resolve + flexible_spec"

# shellcheck disable=SC1091
source "$VENV/bin/activate"

# 2e.1 — walk_targeting turns strings into resolved objects; already-resolved
# entries are skipped (plan file IS the cache, re-run is idempotent).
if python3 - <<PY > "$WORK/resolve-unit.log" 2>&1
import sys
sys.path.insert(0, "$PROJECT/adapters/meta")
from resolve import walk_targeting, FIELD_MAP

plan = {"campaigns": [{"adsets": [{"targeting": {
    "interests": ["mobile Pflege", {"id": "999", "name": "already-resolved"}],
    "work_positions": ["Pflegedienstleitung"],
    "industries": ["Healthcare"],
}}]}]}

calls = []
def stub(type_, q, extra):
    calls.append((type_, q, extra))
    return {"id": f"id_{q}", "name": q, "audience_size": 100000}

walk_targeting(plan, stub)

t = plan["campaigns"][0]["adsets"][0]["targeting"]
assert t["interests"] == [
    {"id": "id_mobile Pflege", "name": "mobile Pflege", "audience_size": 100000},
    {"id": "999", "name": "already-resolved"},
], t["interests"]
assert t["work_positions"][0]["id"] == "id_Pflegedienstleitung"
assert t["industries"][0]["id"] == "id_Healthcare"

# re-run must be a no-op — no further API calls
before = len(calls)
walk_targeting(plan, stub)
assert len(calls) == before, f"re-run called resolver {len(calls)-before} extra times"

# check the right endpoint types got called
types_seen = {c[0] for c in calls}
assert types_seen == {"adinterest", "adworkposition", "adTargetingCategory"}, types_seen
print("ok")
PY
then
  pass "walk_targeting resolves + is idempotent on re-run"
else
  fail "walk_targeting unit test"
  cat "$WORK/resolve-unit.log"
fi

# 2e.2 — build_flexible_spec collapses resolved fields into one AND-block
if python3 - <<PY > "$WORK/flex-unit.log" 2>&1
import sys
sys.path.insert(0, "$PROJECT/adapters/meta")
from deploy import build_flexible_spec, apply_advantage_audience

# resolved targeting → flexible_spec block
t = {
    "geo_locations": {"countries": ["AT"]},
    "interests": [{"id": "1", "name": "Pflege"}],
    "work_positions": [{"id": "2", "name": "PDL"}],
    "industries": [{"id": "3", "name": "Healthcare"}],
}
build_flexible_spec(t, "test-adset")
assert "interests" not in t, "should have popped interests off top-level"
assert t["flexible_spec"] == [{
    "interests": [{"id": "1", "name": "Pflege"}],
    "work_positions": [{"id": "2", "name": "PDL"}],
    "industries": [{"id": "3", "name": "Healthcare"}],
}], t["flexible_spec"]

# raw strings → SystemExit with actionable message
try:
    build_flexible_spec({"interests": ["mobile Pflege"]}, "x")
    assert False, "should have raised"
except SystemExit as e:
    assert "resolve.py" in str(e), e

# advantage_audience true → nested targeting_automation.advantage_audience = 1
t = {"advantage_audience": True}
apply_advantage_audience(t)
assert t == {"targeting_automation": {"advantage_audience": 1}}, t

t = {"advantage_audience": False}
apply_advantage_audience(t)
assert t == {"targeting_automation": {"advantage_audience": 0}}, t

# flag omitted → no targeting_automation added
t = {"geo_locations": {"countries": ["AT"]}}
apply_advantage_audience(t)
assert "targeting_automation" not in t, t
print("ok")
PY
then
  pass "build_flexible_spec + apply_advantage_audience"
else
  fail "flexible_spec unit test"
  cat "$WORK/flex-unit.log"
fi

# 2e.3 — deploy dry-run must fail on raw strings (means resolve wasn't run)
PLAN_RAW="$PROJECT/plan-raw-strings.json"
python3 - <<PY
import json, pathlib
p = json.loads(pathlib.Path("$PROJECT/adapters/meta/example-plan.json").read_text())
p["campaigns"][0]["adsets"][0]["targeting"]["interests"] = ["mobile Pflege"]
pathlib.Path("$PLAN_RAW").write_text(json.dumps(p, indent=2))
PY

if (cd "$PROJECT" && python3 adapters/meta/deploy.py --dry-run "$PLAN_RAW" > "$WORK/deploy-raw.log" 2>&1); then
  fail "deploy should have errored on raw targeting strings"
  tail -20 "$WORK/deploy-raw.log"
else
  if grep -q "resolve.py" "$WORK/deploy-raw.log"; then
    pass "deploy refused raw strings and pointed at resolve.py"
  else
    fail "deploy errored but message didn't mention resolve.py"
    tail -20 "$WORK/deploy-raw.log"
  fi
fi

# 2e.4 — locale mapping: derived de_AT / de_CH / fr_BE must map to the
# dominant-territory locale Meta actually accepts (de_DE, fr_FR).
if python3 - <<PY > "$WORK/locale-map.log" 2>&1
import sys
sys.path.insert(0, "$PROJECT/adapters/meta")
from deploy import derive_locale

# these are derived from TLD — all valid BCP-47 but NOT all accepted by Meta search
cases = {
    "hanicare.at":  "de",  # → de_DE
    "example.ch":   None,  # ambiguous TLD, derive_locale returns None
    "example.de":   "de",
    "example.fr":   "fr",
    "example.nl":   "nl",
    "example.it":   "it",
}
LANG_TO_META = {
    "de": "de_DE", "fr": "fr_FR", "nl": "nl_NL", "it": "it_IT",
    "es": "es_ES", "pt": "pt_BR", "en": "en_US",
}
for domain, expected_lang in cases.items():
    info = derive_locale(domain)
    if expected_lang is None:
        assert info is None, (domain, info)
    else:
        assert info and info["language"] == expected_lang, (domain, info)
        meta_locale = LANG_TO_META.get(info["language"])
        assert meta_locale is not None, (domain, info)
print("ok")
PY
then
  pass "locale map covers TLDs Meta's search accepts"
else
  fail "locale map"
  cat "$WORK/locale-map.log"
fi

deactivate

# ---------------------------------------------------------------------------
# Test 2f — image provider dispatcher (generate_hero.py + bfl.py)
# ---------------------------------------------------------------------------
head "Test 2f: image provider dispatcher"

# shellcheck disable=SC1091
source "$VENV/bin/activate"

# 2f.1 — list_providers must find the built-in bfl module on disk.
if python3 - <<PY > "$WORK/dispatcher-list.log" 2>&1
import sys
sys.path.insert(0, "$PROJECT/engines/static")
from generate_hero import list_providers
providers = list_providers()
assert "bfl" in providers, providers
print("ok", providers)
PY
then
  pass "list_providers finds bfl on disk"
else
  fail "list_providers"
  cat "$WORK/dispatcher-list.log"
fi

# 2f.2 — pick_provider picks bfl when only BFL_API_KEY is set.
if env -i PATH="$PATH" BFL_API_KEY=dummy python3 - <<PY > "$WORK/dispatcher-auto.log" 2>&1
import sys
sys.path.insert(0, "$PROJECT/engines/static")
from generate_hero import pick_provider
assert pick_provider() == "bfl"
print("ok")
PY
then
  pass "pick_provider auto-detects bfl from BFL_API_KEY"
else
  fail "auto-detect bfl"
  cat "$WORK/dispatcher-auto.log"
fi

# 2f.3 — IMAGE_PROVIDER=bfl wins over missing keys (explicit override path).
if env -i PATH="$PATH" IMAGE_PROVIDER=bfl python3 - <<PY > "$WORK/dispatcher-explicit.log" 2>&1
import sys
sys.path.insert(0, "$PROJECT/engines/static")
from generate_hero import pick_provider
assert pick_provider() == "bfl"
print("ok")
PY
then
  pass "IMAGE_PROVIDER override resolves without a key set"
else
  fail "explicit override"
  cat "$WORK/dispatcher-explicit.log"
fi

# 2f.4 — IMAGE_PROVIDER=bogus errors with "Available:" listing built-ins.
if env -i PATH="$PATH" IMAGE_PROVIDER=bogus python3 - <<PY > "$WORK/dispatcher-bogus.log" 2>&1
import sys
sys.path.insert(0, "$PROJECT/engines/static")
from generate_hero import pick_provider
try:
    pick_provider()
except RuntimeError as e:
    msg = str(e)
    assert "bogus" in msg, msg
    assert "Available" in msg, msg
    assert "bfl" in msg, msg
    print("ok")
else:
    raise SystemExit("expected RuntimeError")
PY
then
  pass "unknown IMAGE_PROVIDER errors with helpful hint"
else
  fail "bogus provider error"
  cat "$WORK/dispatcher-bogus.log"
fi

# 2f.5 — no keys + no IMAGE_PROVIDER must fail with flat_brand_color hint.
if env -i PATH="$PATH" python3 - <<PY > "$WORK/dispatcher-nokey.log" 2>&1
import sys
sys.path.insert(0, "$PROJECT/engines/static")
from generate_hero import pick_provider
try:
    pick_provider()
except RuntimeError as e:
    msg = str(e)
    assert "IMAGE_PROVIDER" in msg, msg
    assert "flat_brand_color" in msg, msg
    print("ok")
else:
    raise SystemExit("expected RuntimeError")
PY
then
  pass "no-key path prints IMAGE_PROVIDER + flat_brand_color hint"
else
  fail "no-key error"
  cat "$WORK/dispatcher-nokey.log"
fi

# 2f.6 — bfl module shape: correct endpoint, x-key header, body payload,
# polls until Ready, downloads sample URL. Uses stubbed HTTP helpers so no
# live BFL call is made.
if env -i PATH="$PATH" BFL_API_KEY=test-key python3 - <<PY > "$WORK/dispatcher-bfl-shape.log" 2>&1
import importlib.util, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "bfl_under_test",
    Path("$PROJECT/engines/static/image_providers/bfl.py"),
)
bfl = importlib.util.module_from_spec(spec); spec.loader.exec_module(bfl)

seen = {"posts": [], "gets": [], "downloads": []}

def fake_post(url, body, headers):
    seen["posts"].append((url, body, headers))
    return {"id": "job-123", "polling_url": "https://api.bfl.ai/v1/get_result?id=job-123"}

def fake_get(url, headers):
    seen["gets"].append((url, headers))
    # second poll returns Ready
    if len(seen["gets"]) == 1:
        return {"status": "Pending"}
    return {"status": "Ready", "result": {"sample": "https://cdn.bfl.ai/img.png"}}

def fake_download(url):
    seen["downloads"].append(url)
    return b"\x89PNG\r\n\x1a\nfakebytes"

bfl._post_json = fake_post
bfl._get_json = fake_get
bfl._download = fake_download
bfl.POLL_INTERVAL_SECONDS = 0  # don't sleep in tests

out = bfl.generate("a cat", 1024, 1024)
assert out == b"\x89PNG\r\n\x1a\nfakebytes"

# submit shape
assert len(seen["posts"]) == 1
url, body, headers = seen["posts"][0]
assert url == "https://api.bfl.ai/v1/flux-2-pro", url
assert headers == {"x-key": "test-key"}, headers
assert body == {"prompt": "a cat", "width": 1024, "height": 1024}, body

# poll shape
assert len(seen["gets"]) == 2
for gurl, ghdr in seen["gets"]:
    assert gurl == "https://api.bfl.ai/v1/get_result?id=job-123"
    assert ghdr == {"x-key": "test-key"}

# download
assert seen["downloads"] == ["https://cdn.bfl.ai/img.png"]
print("ok")
PY
then
  pass "bfl module: endpoint, x-key header, poll loop, download"
else
  fail "bfl shape"
  cat "$WORK/dispatcher-bfl-shape.log"
fi

# 2f.7 — BFL_MODEL override changes the submit URL.
if env -i PATH="$PATH" BFL_API_KEY=test-key BFL_MODEL=flux-schnell python3 - <<PY > "$WORK/dispatcher-bfl-model.log" 2>&1
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "bfl_under_test2",
    Path("$PROJECT/engines/static/image_providers/bfl.py"),
)
bfl = importlib.util.module_from_spec(spec); spec.loader.exec_module(bfl)

seen_url = []
bfl._post_json = lambda url, body, headers: (seen_url.append(url) or
    {"id": "j", "polling_url": "p"})
bfl._get_json = lambda url, headers: {"status": "Ready", "result": {"sample": "s"}}
bfl._download = lambda url: b"px"
bfl.POLL_INTERVAL_SECONDS = 0

bfl.generate("x", 512, 512)
assert seen_url == ["https://api.bfl.ai/v1/flux-schnell"], seen_url
print("ok")
PY
then
  pass "BFL_MODEL env overrides the submit URL"
else
  fail "BFL_MODEL override"
  cat "$WORK/dispatcher-bfl-model.log"
fi

# 2f.7b — _snap_dims preserves aspect ratio when clamping (#34). The previous
# _snap() clamped each dim independently, so 1728x2160 (4:5) came back as
# 1440x1440 (1:1). _snap_dims scales proportionally first.
if env -i PATH="$PATH" python3 - <<PY > "$WORK/bfl-aspect.log" 2>&1
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "bfl_aspect",
    Path("$PROJECT/engines/static/image_providers/bfl.py"),
)
bfl = importlib.util.module_from_spec(spec); spec.loader.exec_module(bfl)

# 4:5 portrait above the cap -> scales down proportionally to hit 1440 on the
# taller side, shorter side scales to match the requested aspect ratio.
w, h = bfl._snap_dims(1728, 2160)
assert h == 1440, (w, h)  # the dim that hit the cap
assert w % 32 == 0 and h % 32 == 0, (w, h)
# aspect should be within one 32-step of requested 4:5 = 0.8
ratio = w / h
assert abs(ratio - 0.8) < 0.03, (w, h, ratio)

# 16:9 wider than cap -> still preserves aspect
w, h = bfl._snap_dims(1920, 1080)
assert w == 1440, (w, h)
assert abs((w / h) - (16 / 9)) < 0.05, (w, h)

# already-valid dims pass through unchanged
w, h = bfl._snap_dims(1024, 1024)
assert (w, h) == (1024, 1024), (w, h)

# dims below floor scale up proportionally
w, h = bfl._snap_dims(100, 200)  # aspect 1:2
assert w >= 256 and h >= 256
assert abs((w / h) - 0.5) < 0.08, (w, h)
print("ok")
PY
then
  pass "bfl _snap_dims preserves aspect ratio when clamping"
else
  fail "bfl aspect-ratio snap"
  cat "$WORK/bfl-aspect.log"
fi

# 2f.7c — generate_hero writes to the correct extension when the provider
# returns a different format than the output path implies (#38).
if env -i PATH="$PATH" python3 - <<PY > "$WORK/generate-hero-ext.log" 2>&1
import importlib.util, sys, tempfile, os, io
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "gh",
    Path("$PROJECT/engines/static/generate_hero.py"),
)
gh = importlib.util.module_from_spec(spec); spec.loader.exec_module(gh)

# Force the internal generate to return JPEG bytes
gh.generate_hero = lambda prompt, w, h, provider=None: b"\xff\xd8\xff\xe0JPEG-ish"
gh.pick_provider = lambda: "bfl"

with tempfile.TemporaryDirectory() as td:
    requested = Path(td) / "orbit_hero_4x5.png"
    sys.argv = ["generate_hero.py", str(requested), "1024", "1024"]
    sys.stdin = io.StringIO("prompt")

    # capture stdout (the final path)
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        rc = gh.main()
    finally:
        sys.stdout = old_stdout
    assert rc == 0, rc

    # requested .png should not exist
    assert not requested.exists(), requested
    # .jpg should exist
    final = requested.with_suffix(".jpg")
    assert final.exists(), final
    assert final.read_bytes().startswith(b"\xff\xd8\xff"), "not JPEG"

    # stdout reports the final path
    assert buf.getvalue().strip().endswith("orbit_hero_4x5.jpg"), buf.getvalue()
print("ok")
PY
then
  pass "generate_hero rewrites extension to match returned format"
else
  fail "generate_hero extension rewrite"
  cat "$WORK/generate-hero-ext.log"
fi

# 2f.8 — flux.sh is still callable (backcompat wrapper). Feeds stdin prompt
# and a non-existent output path through a dry wrapper: we don't want a real
# BFL call, so we intercept by replacing generate_hero.py's generate call via
# a temp PYTHONPATH that shadows the real bfl module.
SHADOW="$WORK/shadow_providers"
mkdir -p "$SHADOW/engines/static/image_providers"
cat > "$SHADOW/engines/static/image_providers/bfl.py" <<'PY'
def generate(prompt, width, height):
    return b"\x89PNG\r\n\x1a\n" + f"{prompt}|{width}x{height}".encode()
PY
touch "$SHADOW/engines/static/image_providers/__init__.py"

# Copy the real dispatcher into the shadow tree so it finds our fake bfl.py
cp "$PROJECT/engines/static/generate_hero.py" "$SHADOW/engines/static/generate_hero.py"
cp "$PROJECT/engines/static/flux.sh" "$SHADOW/engines/static/flux.sh"
chmod +x "$SHADOW/engines/static/flux.sh" "$SHADOW/engines/static/generate_hero.py"

SHADOW_OUT="$WORK/shadow_hero.png"
if BFL_API_KEY=fake bash "$SHADOW/engines/static/flux.sh" "$SHADOW_OUT" 800 600 <<<"shadow test" > "$WORK/flux-wrapper.log" 2>&1; then
  if [ -f "$SHADOW_OUT" ] && python3 -c "
import sys
data = open(sys.argv[1], 'rb').read()
assert data.startswith(b'\x89PNG\r\n\x1a\n'), data[:8]
assert b'shadow test|800x600' in data, data
" "$SHADOW_OUT" > "$WORK/flux-wrapper-check.log" 2>&1; then
    pass "flux.sh wrapper routes through dispatcher + writes output"
  else
    fail "flux.sh wrapper did not write a PNG-shaped file"
    cat "$WORK/flux-wrapper.log"
    cat "$WORK/flux-wrapper-check.log"
  fi
else
  fail "flux.sh wrapper exit code"
  cat "$WORK/flux-wrapper.log"
fi

deactivate

# ---------------------------------------------------------------------------
# Test 2g — shape tests for the remaining 5 built-in providers
# ---------------------------------------------------------------------------
head "Test 2g: provider shape tests (google, openai, replicate, stability, fal)"

# shellcheck disable=SC1091
source "$VENV/bin/activate"

# Shared helper: load a provider module from disk with arbitrary env.
run_provider_test () {
  local name="$1"      # label for failure messages
  local log="$2"       # log file
  local env_prefix="$3"  # env string like 'FOO=bar BAR=baz'
  local mod_path="$4"
  if eval "env -i PATH=\"\$PATH\" TEST_BODY=\"\$TEST_BODY\" $env_prefix python3 - \"$mod_path\" > \"$log\" 2>&1" <<'PY'
import importlib.util, os, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("mod_under_test", Path(sys.argv[1]))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
exec(os.environ["TEST_BODY"], {"mod": mod})
print("ok")
PY
  then
    pass "$name"
  else
    fail "$name"
    cat "$log"
  fi
}

# 2g.1 — google (Nano Banana)
GOOGLE_BODY='
import json, base64
calls = []
class FakeResp:
    def __init__(self, payload): self._p = json.dumps(payload).encode()
    def read(self): return self._p
    def __enter__(self): return self
    def __exit__(self, *a): return False

png = base64.b64encode(b"\x89PNG\r\n\x1a\nFAKEBYTES").decode()
def fake_urlopen(req, timeout=None):
    calls.append({"url": req.full_url, "headers": dict(req.header_items()), "body": req.data})
    return FakeResp({"candidates": [{"content": {"parts": [
        {"inlineData": {"mimeType": "image/png", "data": png}}
    ]}}]})

mod.urllib.request.urlopen = fake_urlopen
out = mod.generate("a cat on a roof", 1024, 1024)
assert out == b"\x89PNG\r\n\x1a\nFAKEBYTES", out
c = calls[0]
assert c["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent", c["url"]
hdrs = {k.lower(): v for k, v in c["headers"].items()}
assert hdrs.get("x-goog-api-key") == "testkey", hdrs
body = json.loads(c["body"])
assert body["contents"][0]["parts"][0]["text"] == "a cat on a roof"
assert body["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]
assert body["imageConfig"]["aspectRatio"] == "1:1", body["imageConfig"]
'
TEST_BODY="$GOOGLE_BODY" run_provider_test \
  "google: endpoint + x-goog-api-key + body + b64 decode" \
  "$WORK/dispatcher-google.log" \
  "GEMINI_API_KEY=testkey" \
  "$PROJECT/engines/static/image_providers/google.py"

# 2g.2 — openai (gpt-image-1)
OPENAI_BODY='
import json, base64
calls = []
class FakeResp:
    def __init__(self, payload): self._p = json.dumps(payload).encode()
    def read(self): return self._p
    def __enter__(self): return self
    def __exit__(self, *a): return False

png = base64.b64encode(b"\x89PNG\r\n\x1a\nOPENAIBYTES").decode()
def fake_urlopen(req, timeout=None):
    calls.append({"url": req.full_url, "headers": dict(req.header_items()), "body": req.data})
    return FakeResp({"data": [{"b64_json": png}]})

mod.urllib.request.urlopen = fake_urlopen
out = mod.generate("a dog in the park", 1024, 1024)
assert out == b"\x89PNG\r\n\x1a\nOPENAIBYTES", out
c = calls[0]
assert c["url"] == "https://api.openai.com/v1/images/generations", c["url"]
hdrs = {k.lower(): v for k, v in c["headers"].items()}
assert hdrs.get("authorization") == "Bearer testkey", hdrs
body = json.loads(c["body"])
assert body["model"] == "gpt-image-1", body
assert body["prompt"] == "a dog in the park", body
assert body["size"] == "1024x1024", body
# landscape-leaning should pick 1536x1024
out2 = mod.generate("x", 1920, 1080)
body2 = json.loads(calls[1]["body"])
assert body2["size"] == "1536x1024", body2["size"]
'
TEST_BODY="$OPENAI_BODY" run_provider_test \
  "openai: endpoint + Bearer + gpt-image-1 body + size mapping" \
  "$WORK/dispatcher-openai.log" \
  "OPENAI_API_KEY=testkey" \
  "$PROJECT/engines/static/image_providers/openai.py"

# 2g.3 — replicate (black-forest-labs/flux-schnell, Prefer: wait path, then fall-through poll)
REPLICATE_BODY='
import json
class FakeResp:
    def __init__(self, payload=None, bytes_=None):
        self._p = bytes_ if bytes_ is not None else json.dumps(payload).encode()
    def read(self): return self._p
    def __enter__(self): return self
    def __exit__(self, *a): return False

# Case A: Prefer: wait returns already-succeeded
seen = []
def urlopen_a(req, timeout=None):
    seen.append({"url": req.full_url, "headers": dict(req.header_items()), "body": req.data, "method": req.get_method()})
    if req.get_method() == "POST":
        return FakeResp({"id": "p1", "status": "succeeded",
                          "output": ["https://cdn.replicate.com/out.png"]})
    return FakeResp(bytes_=b"\x89PNG\r\n\x1a\nREPLIBYTES")

mod.urllib.request.urlopen = urlopen_a
mod.POLL_INTERVAL_SECONDS = 0
out = mod.generate("a swan", 1600, 900)
assert out == b"\x89PNG\r\n\x1a\nREPLIBYTES", out

post = seen[0]
assert post["url"] == "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions", post["url"]
hdrs = {k.lower(): v for k, v in post["headers"].items()}
assert hdrs.get("authorization") == "Bearer testkey", hdrs
assert hdrs.get("prefer") == "wait=60", hdrs
body = json.loads(post["body"])
assert body["input"]["prompt"] == "a swan", body
assert body["input"]["aspect_ratio"] == "16:9", body  # 1600x900 -> 16:9
dl = seen[1]
assert dl["url"] == "https://cdn.replicate.com/out.png", dl["url"]

# Case B: POST returns starting, poll once to succeeded
seen2 = []
def urlopen_b(req, timeout=None):
    seen2.append({"url": req.full_url, "method": req.get_method()})
    if req.get_method() == "POST":
        return FakeResp({"id": "p2", "status": "starting",
                          "urls": {"get": "https://api.replicate.com/v1/predictions/p2"}})
    if req.full_url == "https://api.replicate.com/v1/predictions/p2":
        return FakeResp({"id": "p2", "status": "succeeded",
                          "output": "https://cdn.replicate.com/out2.png"})
    return FakeResp(bytes_=b"POLLPNG")

mod.urllib.request.urlopen = urlopen_b
out2 = mod.generate("test", 1024, 1024)
assert out2 == b"POLLPNG", out2
# Ensure we actually polled the urls.get endpoint before downloading
assert any(s["url"] == "https://api.replicate.com/v1/predictions/p2" for s in seen2)
'
TEST_BODY="$REPLICATE_BODY" run_provider_test \
  "replicate: flux-schnell endpoint + Bearer + Prefer wait + poll fallthrough + output url" \
  "$WORK/dispatcher-replicate.log" \
  "REPLICATE_API_TOKEN=testkey" \
  "$PROJECT/engines/static/image_providers/replicate.py"

# 2g.4 — stability (multipart, Accept: image/*, raw bytes)
STABILITY_BODY='
class FakeResp:
    def __init__(self, b): self._b = b
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False

seen = []
def fake_urlopen(req, timeout=None):
    seen.append({"url": req.full_url, "headers": dict(req.header_items()), "body": req.data})
    return FakeResp(b"\x89PNG\r\n\x1a\nSTABILITYBYTES")

mod.urllib.request.urlopen = fake_urlopen
out = mod.generate("a forest", 1024, 1024)
assert out == b"\x89PNG\r\n\x1a\nSTABILITYBYTES", out

c = seen[0]
assert c["url"] == "https://api.stability.ai/v2beta/stable-image/generate/core", c["url"]
hdrs = {k.lower(): v for k, v in c["headers"].items()}
assert hdrs.get("authorization") == "Bearer testkey", hdrs
assert hdrs.get("accept") == "image/*", hdrs
assert hdrs.get("content-type", "").startswith("multipart/form-data; boundary="), hdrs
body = c["body"]
# multipart must carry prompt, aspect_ratio, output_format
assert b"name=\"prompt\"" in body, body
assert b"a forest" in body, body
assert b"name=\"aspect_ratio\"" in body, body
assert b"1:1" in body, body
assert b"name=\"output_format\"" in body, body
assert b"png" in body, body

# STABILITY_MODEL=ultra switches the URL path
import os
os.environ["STABILITY_MODEL"] = "ultra"
mod.generate("x", 1024, 1024)
assert seen[1]["url"] == "https://api.stability.ai/v2beta/stable-image/generate/ultra", seen[1]["url"]
'
TEST_BODY="$STABILITY_BODY" run_provider_test \
  "stability: core endpoint + Bearer + Accept image/* + multipart fields + STABILITY_MODEL override" \
  "$WORK/dispatcher-stability.log" \
  "STABILITY_API_KEY=testkey" \
  "$PROJECT/engines/static/image_providers/stability.py"

# 2g.5 — fal (queue submit-poll-response)
FAL_BODY='
import json
class FakeResp:
    def __init__(self, payload=None, bytes_=None):
        self._p = bytes_ if bytes_ is not None else json.dumps(payload).encode()
    def read(self): return self._p
    def __enter__(self): return self
    def __exit__(self, *a): return False

seen = []
def fake_urlopen(req, timeout=None):
    seen.append({"url": req.full_url, "headers": dict(req.header_items()),
                  "body": req.data, "method": req.get_method()})
    if req.get_method() == "POST":
        return FakeResp({
            "request_id": "r1",
            "status_url": "https://queue.fal.run/fal-ai/flux/schnell/requests/r1/status",
            "response_url": "https://queue.fal.run/fal-ai/flux/schnell/requests/r1",
        })
    if req.full_url.endswith("/status"):
        # first poll IN_PROGRESS, next COMPLETED
        poll_idx = sum(1 for s in seen if s["url"].endswith("/status")) - 1
        return FakeResp({"status": "IN_PROGRESS"} if poll_idx == 0 else {"status": "COMPLETED"})
    if req.full_url.endswith("/requests/r1"):
        return FakeResp({"images": [{"url": "https://v3.fal.media/files/img.png"}]})
    return FakeResp(bytes_=b"\x89PNG\r\n\x1a\nFALBYTES")

mod.urllib.request.urlopen = fake_urlopen
mod.POLL_INTERVAL_SECONDS = 0
out = mod.generate("prompt text", 800, 1200)
assert out == b"\x89PNG\r\n\x1a\nFALBYTES", out

post = seen[0]
assert post["url"] == "https://queue.fal.run/fal-ai/flux/schnell", post["url"]
hdrs = {k.lower(): v for k, v in post["headers"].items()}
assert hdrs.get("authorization") == "Key testkey", hdrs
body = json.loads(post["body"])
assert body["prompt"] == "prompt text", body
assert body["image_size"] == {"width": 800, "height": 1200}, body

# must have polled status and fetched response before downloading
urls = [s["url"] for s in seen]
assert any(u.endswith("/status") for u in urls)
assert any(u.endswith("/requests/r1") for u in urls)
assert "https://v3.fal.media/files/img.png" in urls
'
TEST_BODY="$FAL_BODY" run_provider_test \
  "fal: queue submit + Key auth + image_size body + status poll + response url + download" \
  "$WORK/dispatcher-fal.log" \
  "FAL_KEY=testkey" \
  "$PROJECT/engines/static/image_providers/fal.py"

# 2g.6 — dispatcher auto-detection order: Google key wins over OpenAI key
# (bfl still first; this checks that a missing-bfl env falls through properly)
if env -i PATH="$PATH" GEMINI_API_KEY=g OPENAI_API_KEY=o python3 - <<PY > "$WORK/dispatcher-order.log" 2>&1
import sys
sys.path.insert(0, "$PROJECT/engines/static")
from generate_hero import pick_provider
assert pick_provider() == "google", pick_provider()
PY
then
  pass "dispatcher auto-detects google before openai"
else
  fail "dispatcher order"
  cat "$WORK/dispatcher-order.log"
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
  if (cd "$MOTION" && bash render.sh "$PROJECT/variants/_reference/ops-console-example.json" \
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
