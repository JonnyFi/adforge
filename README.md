# adforge

> Brief-to-live-ad pipeline for Meta. Runs inside your agent (Claude Code, Codex, Cursor).

adforge turns a one-line brief into rendered creatives and, with approval, live Meta ads. It's an opinionated pipeline, not a framework — PIL + Remotion for rendering, a small idempotent Meta adapter for deploy, and markdown skills that orchestrate the agent you already use.

## Prerequisites

adforge degrades gracefully — you can start without any keys and still render creatives locally. Here's what unlocks what:

**Runtime (required):**
- Node 18+
- Python 3 with Pillow (`pip install Pillow`)
- ffmpeg (for motion renders)

**API keys (optional, unlock Meta deploy + AI hero images):**

| Key | What it unlocks | How to get it |
|-----|-----------------|---------------|
| `META_ACCESS_TOKEN` | Deploy to Meta, review performance, pause/scale ads | [Meta Business → System User token](https://developers.facebook.com/docs/marketing-api/system-users) with `ads_management` + `pages_read_engagement` scopes |
| `META_AD_ACCOUNT_ID` | Same as above — target account | Ads Manager → Account Settings (format: `act_1234...`) |
| `META_PAGE_ID` | Page to run ads from | Your FB page → About → Page ID |
| `META_PIXEL_ID` *(optional)* | Conversion-optimized campaigns | Events Manager → Data Sources → Pixel ID |
| `BFL_API_KEY` *(optional, tested default)* | AI-generated hero images via Flux | [bfl.ml/api](https://bfl.ml/api) (pay-as-you-go) |

**On hero images:** Flux (BFL) is the tested default — that's what we've validated end-to-end. It's not required. adforge doesn't care where the PNG comes from: drop in OpenAI / Ideogram / Midjourney exports, a Figma render, or a flat `hero_mode: "radiant_gradient"` and the rest of the pipeline works the same.

**Without any keys:** you can still scaffold, render static + motion creatives, and iterate locally. You just can't deploy to Meta or auto-generate heroes inside the pipeline.

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
- **Extensible layouts** — three static layouts out of the box (advertorial / stat-card / quote-card), three motion compositions (ops-console / product-mockup / walkthrough). Drop a new file into `engines/static/layouts/` and it auto-registers. Show the agent a reference creative or describe what you want — `layout-synth` skill drafts a new layout module on the spot.
- **Bring your own creative** — if you already have finished PNGs/MP4s, skip compose entirely; `deploy.py` takes any asset path.
- **Meta adapter** — deploy, review, actions (pause / resume / scale / delete), idempotent by name via `.adforge/state.json`
- **Brand tokens** — one `brand.json` drives both Python and Remotion
- **Agent-portable** — plain markdown skills. No runtime you have to trust.

## Why it exists

Running ads manually is tedious: assembling creatives in Canva or Figma, writing copy from scratch, keeping every variant on brand, uploading to Ads Manager one by one, and then circling back every few days to read the same insights screen. Most of that is mechanical.

And every time you touch a new agent or a new ad account, you end up rebuilding the same 6 things: a brief flow, a couple of static templates, a motion template, a Meta deploy script that doesn't duplicate ads, a review loop, a state file.

adforge is that stack, extracted once, reusable. Tell an agent what you want, get rendered creatives on-brand, deploy idempotently, review in the same session.

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
