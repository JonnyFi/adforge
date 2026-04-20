# adforge — agent entry point

This file is for AI coding agents (Codex CLI, Cursor, etc.) working in this project.

## Quickstart

When the user says "adforge", "start adforge", or asks for ads/creatives/campaigns:

→ Read `.claude/skills/adforge/SKILL.md` and follow it.

That is the hub. It routes to 4 mode skills depending on what the user wants:

- `.claude/skills/new-campaign/SKILL.md`
- `.claude/skills/add-creative/SKILL.md`
- `.claude/skills/review-performance/SKILL.md`
- `.claude/skills/setup/SKILL.md`

Mode skills compose 4 backend skills:

- `.claude/skills/creative-director/SKILL.md`
- `.claude/skills/composer-speccer/SKILL.md`
- `.claude/skills/performance-analyst/SKILL.md`
- `.claude/skills/layout-synth/SKILL.md` — synthesize a new static layout from a reference image

## Project shape

- `adforge.config.json` — engine + adapter registry
- `brand.json` — colors, fonts, voice
- `variants/` — user-authored ad specs (JSON)
- `engines/static/compose.py` — PIL renderer (advertorial, stat-card, quote-card)
- `engines/motion/` — Remotion project (ops-console, product-mockup, walkthrough)
- `adapters/meta/` — deploy.py, review.py, actions.py (Graph API v21.0)
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
