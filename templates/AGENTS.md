# adforge — agent entry point

This file is for AI coding agents (Codex CLI, Cursor, etc.) working in this project.

## Quickstart

When the user asks for anything involving ads, creatives, variants, statics, motion, reels, hero images, or campaigns in this project — in any phrasing, not just the literal word "adforge":

→ Read `.claude/skills/adforge/SKILL.md` FIRST and follow it.

Examples that route through the hub: "make me a static", "draft an ad for X", "generate a reel", "I want something wild with a supernova", "new creative for the winter campaign", "turn this reference into an ad". Even a one-off "quick test image" goes through the hub — there is no shortcut path.

**Never jump directly to `engines/static/compose.py`, `engines/motion/render.sh`, `generate_hero.py`, or a one-off Python/Node script to produce creatives.** The pipeline is deliberately skill-routed: hub → mode skill (`new-campaign` / `add-creative`) → `composer-speccer` → layout/motion synth when needed. Bypassing it produces template-reskinned output and re-bakes brand-specific work into ad-hoc scripts that no future user inherits.

The hub is the router. It dispatches to 4 mode skills depending on what the user wants:

- `.claude/skills/new-campaign/SKILL.md`
- `.claude/skills/add-creative/SKILL.md`
- `.claude/skills/review-performance/SKILL.md`
- `.claude/skills/setup/SKILL.md`

Mode skills compose 6 backend skills:

- `.claude/skills/creative-director/SKILL.md`
- `.claude/skills/composer-speccer/SKILL.md`
- `.claude/skills/performance-analyst/SKILL.md`
- `.claude/skills/layout-synth/SKILL.md` — synthesize a new static layout from a reference image
- `.claude/skills/motion-synth/SKILL.md` — synthesize a new Remotion composition
- `.claude/skills/image-provider-synth/SKILL.md` — add a new hero-image provider

## Project shape

- `adforge.config.json` — engine + adapter registry
- `brand.json` — colors, fonts, voice
- `variants/` — user-authored ad specs (JSON)
- `engines/static/compose.py` — PIL renderer (advertorial, stat-card, quote-card)
- `engines/motion/` — Remotion project (ops-console, product-mockup, walkthrough)
- `adapters/meta/` — deploy.py, resolve.py, review.py, actions.py (Graph API v22.0). `resolve.py` turns free-form targeting strings (interests, work_positions, industries, behaviors, work_employers) into Meta IDs in place on the plan.
- `.adforge/state.json` — idempotent deploy state (Meta IDs keyed by name)
- `outputs/` — rendered assets

## Rules for agents

- Never call the Meta API without explicit user approval for that specific action.
- Always `--dry-run` before a live deploy.
- Copying `.env.example` → `.env` is fine and expected on first setup; never write secret **values** — the user fills those in. Never echo secrets back.
- Show file diffs before writing any user-content file (variants, plan JSONs).
- Skills are markdown — follow them as instructions, not as templates to quote back.

## Claude Code users

`/adforge` invokes the hub via `.claude/commands/adforge.md`. No extra setup.

## Codex / Cursor / other users

Say: `start adforge` (or equivalent) — the agent will load `.claude/skills/adforge/SKILL.md`.
