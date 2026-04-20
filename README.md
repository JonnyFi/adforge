# adforge

> Brief-to-live-ad pipeline for Meta. Runs inside your agent (Claude Code, Codex, Cursor).

adforge turns a one-line brief into rendered creatives and, with approval, live Meta ads. It's an opinionated pipeline, not a framework — PIL + Remotion for rendering, a small idempotent Meta adapter for deploy, and markdown skills that orchestrate the agent you already use.

## Install

```bash
npx adforge init my-ads
cd my-ads
cp .env.example .env        # fill in keys
```

Then open the project in your agent of choice:

```bash
claude                      # Claude Code → /adforge
codex                       # Codex CLI   → "start adforge"
cursor .                    # Cursor      → "start adforge"
```

The agent reads `.claude/skills/adforge/SKILL.md` (or `AGENTS.md` for Codex) and runs the hub.

## What you get

- **4 user modes** — new-campaign, add-creative, review-performance, setup
- **6 engines** — advertorial / stat-card / quote-card (static PIL) + ops-console / product-mockup / walkthrough (Remotion motion)
- **Meta adapter** — deploy, review, actions (pause / resume / scale / delete), idempotent by name via `.adforge/state.json`
- **Brand tokens** — one `brand.json` drives both Python and Remotion
- **Agent-portable** — plain markdown skills. No runtime you have to trust.

## Why it exists

Every time you touch a new agent or a new ad account, you end up rebuilding the same 6 things: a brief flow, a couple of static templates, a motion template, a Meta deploy script that doesn't duplicate ads, a review loop, a state file. adforge is that stack, extracted once, reusable.

## Commands

```bash
npx adforge init <dir>      # scaffold a new project
npx adforge doctor          # check Python, Node, ffmpeg, env vars
npx adforge --version
```

Everything else — rendering, deploying, reviewing — happens through the agent, or directly via the scripts in `engines/` and `adapters/`.

## Project shape (after init)

```
adforge.config.json   engine + adapter registry
brand.json            colors, fonts, voice
variants/             one JSON per creative
engines/static/       PIL composer
engines/motion/       Remotion project
adapters/meta/        deploy, review, actions
outputs/              rendered PNGs and MP4s
.adforge/state.json   Meta IDs keyed by name
.claude/skills/       agent skills (hub + modes + backend)
AGENTS.md             Codex / Cursor entry
```

## Status

Early. Works for the workflows above. No non-Meta channels yet — the adapter layer is deliberately thin so forks can add TikTok, LinkedIn, Google, etc. PRs welcome.

## License

MIT
