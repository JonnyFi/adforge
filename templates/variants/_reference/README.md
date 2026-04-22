# variants/_reference/ — shape references, not templates

Every file in this folder is a **reference implementation** — it exists so an agent or user can see the JSON *shape* a given layout or composition expects. They are not starting points to copy-paste for a new brand.

## Why the underscore + subfolder

Claude Code, Codex, Cursor, and other agents scan `variants/` when asked to draft an ad. Sibling files at the top level get treated as "available templates to reuse". Moving the references under `_reference/` signals:

- The folder name starts with `_` → conventionally "internal / not user content".
- The files aren't adjacent to the user's real variants → no accidental copy-paste.

## What to do instead

For a new brand's creative, invoke the skill chain:

```
adforge (hub) → new-campaign | add-creative → composer-speccer
  ↘ if no existing layout fits: layout-synth (static) / motion-synth (motion)
```

`composer-speccer` produces a new variant file under `variants/<id>.json` driven by the brand's brief — it may read these reference files to see what fields a layout expects, but it will never copy one wholesale.

## What's in here

| File | What it references |
| --- | --- |
| `example.json` | `advertorial` layout — editorial ad with dateline + body |
| `ops-console-example.json` | `ops-console` motion composition (dispatcher-style UI demo) |
| `quote-card-example.json` | `quote-card` layout — single-sentence pull-quote |
| `stat-card-example.json` | `stat-card` layout — giant number as focal point |

The CI smoke variant (`../walkthrough-ci-smoke.json`) stays in `variants/` because it's release-pipeline infrastructure, not a creative reference.
