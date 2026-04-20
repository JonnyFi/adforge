---
name: setup
description: First-time onboarding — API keys, brand tokens, font files, dry-run verification. Invoked from hub when .env is missing or user asks for setup.
---

# setup

Onboard a new user. Keys first (so FLUX and Meta work downstream), then brand and fonts, then a dry-run to prove the pipeline renders.

## 1. Check runtime

Run `adforge doctor` (or the equivalent checks inline): Node 18+, Python 3, pip, ffmpeg, and Playwright (for brand extraction from JS-rendered sites). Missing → tell the user what to install. Playwright is optional but strongly recommended — without it, brand extraction falls back to plain HTML and breaks on any modern site.

## 2. API keys — first thing, before anything else renders

If `.env` is missing but `.env.example` exists, copy it: `cp .env.example .env`. Then open `.env` and walk through keys **one at a time**. Never echo secrets back, never write values yourself — only the user fills them. Your job is to explain what each key is and where to find it.

For every key, if the user asks "was ist das" or "where do I get that", walk them through the exact click-path below. Do not skim.

### `BFL_API_KEY` (optional — unlocks FLUX hero images)

- What it is: Black Forest Labs API key. Without it, creatives render with flat brand-color backgrounds instead of generated hero images.
- Where to get it: https://dashboard.bfl.ai → sign up → API Keys → Create Key. Pay-as-you-go, ~1ct per image.
- If skipped: creatives still render, just with `hero_mode: "flat_brand_color"`. Fine for MVP, upgrade later.

### `META_ACCESS_TOKEN` (required for deploy)

- What it is: long-lived access token for the Meta Marketing API.
- Where to get it:
  1. https://business.facebook.com → Settings → Users → System Users → Add.
  2. Give the system user the `ads_management`, `ads_read`, `business_management`, `pages_show_list`, `pages_manage_ads` scopes.
  3. Assign it to your Ad Account (Settings → Accounts → Ad Accounts → Assign Partners / People).
  4. Back on the System User → Generate New Token → pick the app → select the scopes above → copy the token.
- Scopes: `ads_management` is the critical one. Without it, every deploy call 403s.

### `META_AD_ACCOUNT_ID` (required for deploy)

- What it is: your Meta ad account ID, prefixed with `act_`.
- Where to get it: https://business.facebook.com → Ads Manager → the URL contains `act=1234...`, or Settings → Ad Accounts → Account ID. Format: `act_1234567890`.

### `META_PAGE_ID` (required for deploy)

- What it is: the Facebook Page the ads run from.
- Where to get it: open your FB page → About tab → scroll to "Page transparency" or "Page ID" near the bottom.

### `META_PIXEL_ID` (optional — only for conversion-optimized campaigns)

- What it is: Meta Pixel ID, needed when optimisation goal is `OFFSITE_CONVERSIONS` (e.g. Lead or Purchase).
- Where to get it: https://business.facebook.com → Events Manager → Data Sources → pick your pixel → ID in the top-right.
- If skipped: traffic-optimized campaigns still work; conversion-optimized adsets will fail on deploy.

When done, confirm each key is present (grep-test the `.env` file, don't echo values). Flag which optional keys are missing and what that limits.

## 3. Brand

Extract brand tokens from the user's domain. Use Playwright first (handles JS-rendered sites — most modern sites won't give you usable CSS via plain fetch). Fallback order:

1. `playwright` via Python: launch headless Chromium, navigate, read computed styles of `h1`, primary button, body.
2. Screenshot + vision parse if computed styles are inconclusive.
3. `curl` + HTML scrape only if Playwright isn't installed — warn the user this will be wrong on most modern sites.

Then open `brand.json` and walk the user through customising:
- **name, wordmark, domain**. The domain is load-bearing — `adapters/meta/deploy.py` reads it to auto-default `geo_locations.countries` for every adset. See the TLD table below.
- **colors** (ink, muted, cream, accent) — hex only.
- **voice principles** (1–3 short rules) and **voice.locale** (copy language — `de`, `en`, `fr`, …). Derive from the same TLD mapping.

**TLD → locale mapping** (same table `deploy.py::derive_locale` uses — apply deterministically, don't ask):

| TLD | country | voice.locale |
|-----|---------|--------------|
| `.at` | AT | de |
| `.de` | DE | de |
| `.fr` | FR | fr |
| `.es` | ES | es |
| `.it` | IT | it |
| `.nl` | NL | nl |
| `.co.uk` / `.uk` | GB | en |
| `.ie` | IE | en |
| `.us` | US | en |
| `.pl` | PL | pl |
| `.pt` | PT | pt |
| `.se` | SE | sv |
| `.no` | NO | no |
| `.dk` | DK | da |
| `.fi` | FI | fi |

**Ambiguous TLDs** (`.com`, `.io`, `.co`, `.app`, `.net`, `.ai`, `.ch`, `.be`, …) — *always* ask the user where they sell and what language they write in. `deploy.py` will refuse to auto-pick a country for these and require `targeting.geo_locations.countries` in the plan.

Show the diff before writing.

## 4. Chrome — brand mark on every creative (opt-in)

Ask the user (in their `voice.locale` — translate the prompt if locale is non-English):

> Do you want a brand mark on every ad, or should each ad stand on its own?
>
> - **a)** No recurring mark. Each ad is structurally self-contained. Recommended when testing many angles — less "same adforge look" across ads.
> - **b)** Text wordmark — your `wordmark` or `name` written in a corner.
> - **c)** Logo image — you drop in a PNG, adforge places it on every ad.
> - **d)** Not sure, decide for me → defaults to (b): text wordmark, bottom-left, serif-italic, accent color, 64px.

Don't configure chrome unless the user picks (b), (c), or (d). No chrome block = naked canvas, which is the right default for most first-time users.

### If (b) — text wordmark

Pick sensible defaults, only ask the user to override if they want. Write this to `brand.json`:

```json
"chrome": {
  "wordmark": {
    "show": true,
    "position": "bottom-left",
    "style": "serif-italic",
    "color": "accent",
    "fontSize": 64,
    "padding": 180
  }
}
```

Offer variants only if the user pushes back:
- `position`: `top-left`, `top-center`, `top-right`, `bottom-left`, `bottom-center`, `bottom-right`
- `style`: `serif-italic` (Instrument Serif italic), `sans-medium` (Inter medium), `mono-uppercase` (JetBrains Mono, upper-cased + tracked)
- `color`: `accent`, `ink`, `muted`, or any hex

### If (c) — logo image

1. Ask the user to drop a logo PNG into `./assets/` at project root (create the dir if missing). Transparent background works best.
2. Write this, substituting the filename:

```json
"chrome": {
  "wordmark": {
    "show": true,
    "position": "bottom-left",
    "path": "assets/logo.png",
    "height": 140,
    "padding": 120
  }
}
```

The same path resolves in both engines — `render.sh` auto-syncs `assets/` into `engines/motion/public/assets/` on each render.

### If (d) — let adforge decide

Just write option (b)'s text-wordmark config. Tell the user: "If you ship a batch and the text wordmark feels off, come back and switch to a logo image or turn it off — it's a one-line edit in `brand.json`."

## 5. Fonts

Tell the user: drop `.ttf` files into `./fonts/` matching the names in `brand.json`, or change the names in `brand.json` to match files they already have. Defaults are Google Fonts (Instrument Serif, JetBrains Mono, Inter) — link them to https://fonts.google.com.

## 6. Dry-run

Compose a static creative from `variants/example.json` and a motion from `variants/ops-console-example.json`. Show the user the output files. If that works, setup is done.

Finish: "You're ready. Type 'adforge' anytime to come back to the hub."
