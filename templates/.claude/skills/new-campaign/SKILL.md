---
name: new-campaign
description: End-to-end flow for a brand-new campaign — angle, copy, assets, deploy. Invoked from the adforge hub, not directly.
---

# new-campaign

Walk the user from a fresh idea to a PAUSED campaign on Meta.

## 0. Keys check (non-negotiable, runs first)

Before you interview, before you draft angles, check `.env`:

- No `.env` at all → route to `setup` skill, don't proceed.
- No image-provider key (`BFL_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `REPLICATE_API_TOKEN`, `STABILITY_API_KEY`, or `FAL_KEY`) → hero generation will fall back to `flat_brand_color`. Warn the user before briefing ("creatives will use flat brand-color backgrounds, not AI-generated heroes — set any one of the image-provider keys in .env if you want generated heroes; adforge auto-detects the one you provide, or use `IMAGE_PROVIDER=<name>` to pin it. Bringing a provider adforge doesn't have built-in? Invoke `image-provider-synth`."). Let them decide: proceed without, or pause to add a key.
- No `META_ACCESS_TOKEN` → everything renders locally, but `deploy.py` will only run `--dry-run`. Tell the user they'll need to upload manually or set the token before the deploy stage.

Skipping this check is how you end up generating twelve assets with wrong defaults that have to be thrown away.

## 1. Starting point

Ask one question first — it decides the whole path:

> "What are we working with: (a) start from a fresh brief, (b) match a reference creative you'll show me, or (c) you already have finished assets and just want to deploy?"

Route based on the answer:

### 1a. Fresh brief — standard path

Continue to stage 2 (Brief) → 3 (Angles) → 4 (Assets) → 5 (Plan & deploy). This is the default.

### 1b. Reference creative or open creative request — layout-synth path

Two sub-cases, same destination:

- User shows an image/mockup: read the reference.
- User just *describes* what they want ("a founder quote with my photo and a speech bubble", "a before/after split", "a meme-y thing with a bold caption"): treat the description as the spec.

Then:

- If one of the existing layouts (`advertorial`, `quote-card`, `stat-card`) clearly matches: tell the user, continue to stage 2 with that layout locked in.
- Otherwise: load the **`layout-synth`** skill. It drafts a new module under `engines/static/examples/` and test-renders. Once approved, the new layout name joins the registry — then continue to stage 2 with it.

adforge doesn't pre-enumerate "supported creative concepts". The toolset is: PIL + `shared` primitives for the layout, plus whatever you can install ad-hoc for asset prep (bg-removal, image generation, etc.). If the user's creative ask is feasible with that toolset, say yes and build it. If it genuinely isn't, say so plainly.

### 1c. Bring your own creative — skip compose

User already has PNGs/MP4s ready (from Figma, Canva, a designer, etc.). `deploy.py` takes any `image_path` / `video_path` — no need to go through `compose.py`.

Skip stages 2–4. Go directly to stage 5 (Plan & deploy), but adjust the brief:

- Where do the asset files live? (absolute or project-relative)
- Which format is each asset? (`4x5`, `9x16` — drives placement derivation)
- Primary text, headline, description per ad
- Landing URL per ad
- Daily budget, audience, optimization goal (same questions as standard)

Draft `campaign-plan.json` directly with the user's files referenced, then proceed to deploy.

## 2. Brief

Conduct a short interview. One question at a time:

- What's the campaign about? (one sentence)
- Who is the target audience? (be specific — job, situation, locale)
- What's the landing URL?
- What's the daily budget per adset? (in EUR cents)

If the user is vague, offer 2–3 options to pick from rather than asking open-ended.

## 3. Angles

Load the `creative-director` skill. It proposes 3 angles with hooks and copy drafts. User picks one (or asks to iterate). Each angle becomes one variant.

## 4. Assets

For each angle variant, load the `composer-speccer` skill to translate the copy brief into a concrete variant JSON under `variants/`.

**Format defaults — propose from day one, don't stage rollouts:**

- Render **both `4x5` and `9x16`** for every variant. 4x5 serves Feed (FB + IG); 9x16 serves Stories (and Reels for motion). Meta's delivery rewards multi-placement coverage — launching Feed-only "to see how it does first" is a weaker start, not a safer one.
- Never default to `1x1` (legacy square) — it's downranked across placements.
- Don't ask "should we also do Stories?" as an opt-in. The user can opt *out* if they explicitly don't want a placement, but multi-format is the default.

Render commands:

- **static:** `python3 engines/static/compose.py variants/<id>.json <format> outputs/static/<id>_<format>.png` (run once per format)
- **motion:** `./engines/motion/render.sh variants/<id>.json <composition> outputs/motion/<id>.mp4` (motion renders format-agnostic; the composition defines the aspect)

Show the user the rendered files and let them approve/reject before deploy.

## 5. Plan & deploy

Draft a `campaign-plan.json` (see `adapters/meta/example-plan.json` for shape). Show it as a diff.

### Targeting — free-form, resolved before deploy

Write targeting in plain language — `adapters/meta/resolve.py` turns strings into Meta IDs in a second pass:

```json
"targeting": {
  "geo_locations": {"countries": ["AT"]},
  "interests":      ["mobile Pflege", "Hauskrankenpflege"],
  "work_positions": ["Pflegedienstleitung"],
  "industries":     ["Healthcare Services"],
  "age_min": 28,
  "age_max": 58,
  "advantage_audience": true
}
```

Five resolvable fields: `interests`, `work_positions`, `work_employers`, `industries`, `behaviors`. Write whichever apply — B2B campaigns usually lean on `work_positions` + `industries`, B2C on `interests` + `behaviors`.

**Advantage+ vs. hard targeting.** Ask the user once:

> "Meta has two modes. **Advantage+ Audience** (default) — your targeting is treated as *hints*, Meta's AI expands to similar users that convert. **Hard targeting** — Meta delivers only to people who match. Which do you want?"

Set `advantage_audience: true` for Advantage+, `false` for hard. If skipped, Meta defaults to Advantage+ on v23+ anyway; we set it explicitly so plan behavior is version-independent.

### Custom audiences + lookalikes — optional, plan-level

Retargeting and lookalike scaling lives in a top-level `audiences` block, separate from adset targeting. `deploy.py` creates each audience once (keyed by name in state) and adsets reference them by name in `targeting.custom_audiences` / `targeting.excluded_custom_audiences`.

Four types, all in the same array:

```json
"audiences": [
  {
    "name": "visitors-90d",
    "type": "pixel",
    "retention_days": 90
  },
  {
    "name": "page-engagers-365d",
    "type": "engagement",
    "object_type": "page",
    "object_id": "<META_PAGE_ID>",
    "retention_days": 365
  },
  {
    "name": "customer-list-q1",
    "type": "custom_list",
    "source_csv": "assets/audiences/customers.csv"
  },
  {
    "name": "lookalike-AT-1pct",
    "type": "lookalike",
    "seed": "visitors-90d",
    "country": "AT",
    "ratio": 0.01
  }
]
```

Then reference them in any adset:

```json
"targeting": {
  "custom_audiences": ["lookalike-AT-1pct"],
  "excluded_custom_audiences": ["visitors-90d"]
}
```

Notes:

- `pixel` uses `META_PIXEL_ID` from `.env` unless the audience entry overrides with its own `pixel_id`. Default rule is any PageView.
- `engagement` needs `object_id` + `object_type` (e.g. `page`, `ig_business_profile`, `video`). No defaults — you tell Meta which object's engagers to build from.
- `custom_list` hashes the CSV client-side (SHA-256 of trimmed, lowercase values) and uploads in 10k-row batches. CSV header row defines the schema — `email`, `phone`, `first_name`, `last_name`, `zip`, `country`, etc. Raw PII never leaves the machine.
- `lookalike.seed` is the `name` of another audience in this same `audiences` block. Meta creates seed first, lookalike second — order matters in the array. External seed? Pass `"seed": {"id": "12345"}` instead.
- Custom/lookalike audiences don't go through `resolve.py` — they're created by `deploy.py` itself. `resolve.py` is only for interest-targeting search.
- Don't ask about audiences unprompted on the first campaign. Pure cold-prospect plans should have no `audiences` block at all. Mention this path when the user brings up retargeting, nurture, or scaling a winner.

### Resolve, review, deploy

Two paths depending on whether `META_ACCESS_TOKEN` is set. Tell the user upfront which branch applies:

**With token — auto-resolve (default):**

```bash
# turn strings into {id, name, audience_size} objects in place
python3 adapters/meta/resolve.py campaign-plan.json

# or non-interactive: pick dominant matches automatically, fail on anything ambiguous
python3 adapters/meta/resolve.py --auto campaign-plan.json
```

After resolve, show the plan diff — this is the moment to sanity-check matches (audience sizes, category paths) before spending money.

**Without token — manual UI walk:**

`resolve.py` won't work without the token. The user has to pick IDs in Meta's UI and paste them back. Walk them through it explicitly (don't assume they know where to click):

1. Open https://business.facebook.com/adsmanager/
2. Create a new adset (or edit an existing one) — the interest search only exists inside the adset composer.
3. Scroll to **Audience → Detailed Targeting → Browse** (or type into the search field).
4. For each free-form string in the plan, search it, pick the match, hover the entry — Meta shows the internal ID in the tooltip on some UIs, or you can inspect the DOM (`data-id` attribute on the chip). Alternative: the Facebook Audience API Explorer at https://developers.facebook.com/tools/explorer/ — paste `search?type=adinterest&q=<query>` once the user is logged in, no long-lived token needed for that endpoint.
5. Paste each picked ID back into `campaign-plan.json` as `{"id": "12345", "name": "Pflegedienstleitung"}` — `resolve.py` leaves already-resolved objects alone, so this is a drop-in replacement for the free-form string.

Then deploy flow continues the same way.

**Deploy:**

- `python3 adapters/meta/deploy.py --dry-run campaign-plan.json` — preview API calls (works without token; prints the request shapes)
- `python3 adapters/meta/deploy.py campaign-plan.json` — live, everything PAUSED (needs token)

Deploy refuses to run if it sees raw strings (means resolve wasn't run and the user didn't paste IDs manually either). Manual escape: write an `{"id": "12345", "name": "..."}` object directly in the plan — resolve leaves those alone.

Finish with: "All deployed and paused. To go live, run `python3 adapters/meta/actions.py resume --adset <name>`."
