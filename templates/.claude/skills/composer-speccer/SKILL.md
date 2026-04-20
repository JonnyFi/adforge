---
name: composer-speccer
description: Backend skill — translate an approved angle into a concrete variant JSON in variants/. Used by new-campaign and add-creative.
---

# composer-speccer

Turn a creative brief (from `creative-director`) into a valid variant JSON under `variants/`.

## Inputs

- Angle + hook + body + CTA from creative-director
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

## Process

1. Pick a unique `id` — ask the user to confirm.
2. Draft the JSON. Keep text in whatever language/locale the brief used.
3. Show the diff before writing.
4. For motion variants that need screenshots (walkthrough): ask the user where the images live. Copy them to `engines/motion/public/<subdir>/` and reference with just the subpath. Before picking click-target coordinates, open each screenshot and identify UI elements visually — don't make the user figure out pixel coordinates.
5. Write the file, then tell the caller (`new-campaign` / `add-creative`) which compose command to run.

## Rules

- Never invent hero images. If the brief implies a photo but none is specified, either use `hero_mode: "radiant_gradient"` or prompt-engineer a flux call and ask the user to run it.
- Respect brand colors already in `brand.json` — don't override in variants unless the user explicitly asks.
- Stat-card numbers must be sourced. No numbers without a `source` field.
