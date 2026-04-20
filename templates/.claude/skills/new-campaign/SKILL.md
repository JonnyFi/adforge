---
name: new-campaign
description: End-to-end flow for a brand-new campaign — angle, copy, assets, deploy. Invoked from the adforge hub, not directly.
---

# new-campaign

Walk the user from a fresh idea to a PAUSED campaign on Meta. Four stages.

## 0. Keys check (non-negotiable, runs first)

Before you interview, before you draft angles, check `.env`:

- No `.env` at all → route to `setup` skill, don't proceed.
- No `BFL_API_KEY` → hero generation will fall back to `flat_brand_color`. Warn the user before briefing ("creatives will use flat brand-color backgrounds, not AI-generated heroes — set BFL_API_KEY in .env if you want FLUX heroes"). Let them decide: proceed without, or pause to add the key.
- No `META_ACCESS_TOKEN` → everything renders locally, but `deploy.py` will only run `--dry-run`. Tell the user they'll need to upload manually or set the token before Stage 4.

Skipping this check is how you end up generating twelve assets with wrong defaults that have to be thrown away.

## 1. Brief

Conduct a short interview. Don't ask everything at once — one question at a time:

- What's the campaign about? (one sentence)
- Who is the target audience? (be specific — job, situation, locale)
- What's the landing URL?
- What's the daily budget per adset? (in EUR cents)

If the user is vague, offer 2–3 options to pick from rather than asking open-ended.

## 2. Angles

Load the `creative-director` skill. It proposes 3 angles with hooks and copy drafts. User picks one (or asks to iterate). Each angle becomes one variant.

## 3. Assets

For each angle variant, load the `composer-speccer` skill to translate the copy brief into a concrete variant JSON under `variants/`.

**Format defaults — propose from day one, don't stage rollouts:**

- Render **both `4x5` and `9x16`** for every variant. 4x5 serves Feed (FB + IG); 9x16 serves Stories (and Reels for motion). Meta's delivery rewards multi-placement coverage — launching Feed-only "to see how it does first" is a weaker start, not a safer one.
- Never default to `1x1` (legacy square) — it's downranked across placements.
- Don't ask "should we also do Stories?" as an opt-in. The user can opt *out* if they explicitly don't want a placement, but multi-format is the default.

Render commands:

- **static:** `python3 engines/static/compose.py variants/<id>.json <format> outputs/static/<id>_<format>.png` (run once per format)
- **motion:** `./engines/motion/render.sh variants/<id>.json <composition> outputs/motion/<id>.mp4` (motion renders format-agnostic; the composition defines the aspect)

Show the user the rendered files and let them approve/reject before deploy.

## 4. Plan & deploy

Draft a `campaign-plan.json` (see `adapters/meta/example-plan.json` for shape). Show it as a diff. On approval:

- `python3 adapters/meta/deploy.py --dry-run campaign-plan.json` — preview first
- `python3 adapters/meta/deploy.py campaign-plan.json` — live, everything PAUSED

Finish with: "All deployed and paused. To go live, run `python3 adapters/meta/actions.py resume --adset <name>`."
