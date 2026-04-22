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

For `engine: "static"`, add: `layout` (pick from the registry — see below), `formats` (array), and layout-specific fields. See `variants/_reference/` for the shape of each shipped layout (reference only — never copy wholesale into a new variant).

Available layouts are auto-discovered from `engines/static/examples/`. Shipped as reference implementations: `advertorial`, `quote-card`, `stat-card`. Each module exports a `SCHEMA` dict naming the variant fields it consumes — check the module to see what's expected before drafting. If none of the registered layouts fits the brief, hand off to the `layout-synth` skill first; it will write a new module under `engines/static/examples/` and make it available to the registry.

For `engine: "motion"`, add: `composition` (shipped examples: `ops-console`, `product-mockup`, `walkthrough`, `phone-notifications`) and a `variant` object with the composition's expected shape (see `engines/motion/src/examples/<Name>.tsx` for the type). If none fits, hand off to `motion-synth`.

Brand wordmark placement isn't a variant field — it's configured once in `brand.json → chrome.wordmark` (or omitted for naked creatives). Don't add wordmark text into variants.

## Defaults — follow unless user asks otherwise

- **`formats`: `["4x5", "9x16"]`** — 4x5 goes to Feed (FB + IG), 9x16 goes to Stories (and Reels for motion). Never default to 1x1 (legacy placement, downranked). Never ship only one format "for later" — Meta's delivery rewards multi-placement from day one.
- **`hero_mode`: `"flat_brand_color"`** — clean brand-color background, works without any image-generation key. Use `radiant_gradient` as an explicit stylistic choice; `background` or `top_band` if the user provides a photo; only use `background` with a generated hero if an image-provider key is set (`BFL_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `REPLICATE_API_TOKEN`, `STABILITY_API_KEY`, or `FAL_KEY`) and the user asked for it.
- **`cta`: omit or `""`** — Meta has a platform CTA button on every ad unit. An in-creative CTA text is redundant in most cases, and adds a second focal point that fights the platform button. Only include an in-creative `cta` if the user explicitly asks for one (e.g. stylistic "learn more" link under a pull-quote, or when the layout has no other bottom element).

## Process

1. Pick a unique `id` — ask the user to confirm.
2. Draft the JSON with the defaults above. Keep text in whatever language/locale the brief used.
3. Show the diff before writing.
4. For motion variants that need screenshots (walkthrough): ask the user where the images live. Copy them to `engines/motion/public/<subdir>/` and reference with just the subpath. Before picking click-target coordinates, open each screenshot and identify UI elements visually — don't make the user figure out pixel coordinates.
5. Write the file, then tell the caller (`new-campaign` / `add-creative`) which compose command to run.

## Rules

- Never invent hero images. If the brief implies a photo but none is specified: use `hero_mode: "flat_brand_color"` (default), or if an image-provider key is set and the user wants it, prompt-engineer a hero call — `engines/static/generate_hero.py` dispatches to whichever provider is configured.
- Respect brand colors already in `brand.json` — don't override in variants unless the user explicitly asks.
- Stat-card numbers must be sourced. No numbers without a `source` field.
