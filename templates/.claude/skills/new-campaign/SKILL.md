---
name: new-campaign
description: End-to-end flow for a brand-new campaign — angle, copy, assets, deploy. Invoked from the adforge hub, not directly.
---

# new-campaign

Walk the user from a fresh idea to a PAUSED campaign on Meta. Four stages:

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

For each angle variant, load the `composer-speccer` skill to translate the copy brief into a concrete variant JSON under `variants/`. Then:

- **static:** `python3 engines/static/compose.py variants/<id>.json <format> outputs/static/<id>_<format>.png`
- **motion:** `./engines/motion/render.sh variants/<id>.json <composition> outputs/motion/<id>.mp4`

Show the user the rendered files and let them approve/reject before deploy.

## 4. Plan & deploy

Draft a `campaign-plan.json` (see `adapters/meta/example-plan.json` for shape). Show it as a diff. On approval:

- `python3 adapters/meta/deploy.py --dry-run campaign-plan.json` — preview first
- `python3 adapters/meta/deploy.py campaign-plan.json` — live, everything PAUSED

Finish with: "All deployed and paused. To go live, run `python3 adapters/meta/actions.py resume --adset <name>`."
