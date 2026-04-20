---
name: add-creative
description: Add one new creative (ad) to an already-deployed campaign. Covers the "refresh" case too (replace a fatiguing ad). Invoked from hub.
---

# add-creative

User wants to add a new ad into an existing campaign — either proactively (new idea) or reactively (current ad is fatiguing).

## 1. Context

- Read `.adforge/state.json` — show the user the list of adsets and ask which one to target.
- If this is a refresh (user came here from `review-performance` with a specific underperformer): pre-fill the adset and mention the ad being replaced.

## 2. Brief + compose

Same as `new-campaign` stages 2 and 3 — load `creative-director` for the angle, `composer-speccer` for the variant JSON, then compose and render.

## 3. Deploy

Write a minimal plan JSON that references the existing campaign/adset names (adforge deploy is idempotent on names — it'll skip what exists and only create the new ad). Dry-run first, then live (PAUSED).

After deploy, ask if the user wants to pause an old ad to free up budget.
