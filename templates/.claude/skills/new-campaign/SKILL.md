---
name: new-campaign
description: End-to-end flow for a brand-new campaign — angle, copy, assets, deploy. Invoked from the adforge hub, not directly.
---

# new-campaign

Walk the user from a fresh idea to a PAUSED campaign on Meta.

## 0. Keys check (non-negotiable, runs first)

Before you interview, before you draft angles, check `.env`:

- No `.env` at all → route to `setup` skill, don't proceed.
- No `BFL_API_KEY` → hero generation will fall back to `flat_brand_color`. Warn the user before briefing ("creatives will use flat brand-color backgrounds, not AI-generated heroes — set BFL_API_KEY in .env if you want FLUX heroes — or another image source; adforge doesn't care where the PNG comes from"). Let them decide: proceed without, or pause to add the key.
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
- Otherwise: load the **`layout-synth`** skill. It drafts a new module under `engines/static/layouts/` and test-renders. Once approved, the new layout name joins the registry — then continue to stage 2 with it.

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

Draft a `campaign-plan.json` (see `adapters/meta/example-plan.json` for shape). Show it as a diff. On approval:

- `python3 adapters/meta/deploy.py --dry-run campaign-plan.json` — preview first
- `python3 adapters/meta/deploy.py campaign-plan.json` — live, everything PAUSED

Finish with: "All deployed and paused. To go live, run `python3 adapters/meta/actions.py resume --adset <name>`."
