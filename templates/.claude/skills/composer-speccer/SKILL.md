---
name: composer-speccer
description: Backend skill — translate an approved angle into a concrete variant JSON in variants/. Used by new-campaign and add-creative.
---

# composer-speccer

Turn a creative brief (from `creative-director`) into a valid variant JSON under `variants/`.

## Inputs

- Angle + hook + body from creative-director
- `adforge.config.json` (engines and layouts available)
- User's format choice(s)

## Shape

Every variant file has:

```json
{
  "id": "kebab-case-id",
  "engine": "static" | "motion",
  ...
}
```

For `engine: "static"`, add: `layout` (one of `advertorial`, `stat-card`, `quote-card`), `formats` (array), and layout-specific fields. Look at existing files in `variants/` for reference.

For `engine: "motion"`, add: `composition` (`ops-console`, `product-mockup`, `walkthrough`) and a `variant` object with the composition's expected shape (see `engines/motion/src/engines/<Name>.tsx` for the type).

## Defaults — follow unless user asks otherwise

- **`formats`: `["4x5", "9x16"]`** — 4x5 goes to Feed (FB + IG), 9x16 goes to Stories (and Reels for motion). Never default to 1x1 (legacy placement, downranked). Never ship only one format "for later" — Meta's delivery rewards multi-placement from day one.
- **`hero_mode`: `"flat_brand_color"`** — clean brand-color background, works without FLUX or stock images. Use `radiant_gradient` as an explicit stylistic choice; `background` or `top_band` if the user provides a photo; only use `background` with a FLUX-generated hero if `BFL_API_KEY` is set and the user asked for it.
- **`cta`: omit or `""`** — Meta has a platform CTA button on every ad unit. An in-creative CTA text is redundant in most cases, and adds a second focal point that fights the platform button. Only include an in-creative `cta` if the user explicitly asks for one (e.g. stylistic "learn more" link under a pull-quote, or when the layout has no other bottom element).

## Process

1. Pick a unique `id` — ask the user to confirm.
2. Draft the JSON with the defaults above. Keep text in whatever language/locale the brief used.
3. Show the diff before writing.
4. For motion variants that need screenshots (walkthrough): ask the user where the images live. Copy them to `engines/motion/public/<subdir>/` and reference with just the subpath. Before picking click-target coordinates, open each screenshot and identify UI elements visually — don't make the user figure out pixel coordinates.
5. Write the file, then tell the caller (`new-campaign` / `add-creative`) which compose command to run.

## Rules

- Never invent hero images. If the brief implies a photo but none is specified: use `hero_mode: "flat_brand_color"` (new default), or if `BFL_API_KEY` is set and the user wants it, prompt-engineer a flux call and ask the user to run it.
- Respect brand colors already in `brand.json` — don't override in variants unless the user explicitly asks.
- Stat-card numbers must be sourced. No numbers without a `source` field.
