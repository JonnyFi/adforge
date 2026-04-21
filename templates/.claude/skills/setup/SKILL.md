---
name: setup
description: First-time onboarding — API keys, brand tokens, font files, dry-run verification. Invoked from hub when .env is missing or user asks for setup.
---

# setup

Onboard a new user. Keys first (so image generation and Meta work downstream), then brand and fonts, then a dry-run to prove the pipeline renders.

## 1. Check runtime

Run `adforge doctor` (or the equivalent checks inline): Node 18+, Python 3, pip, ffmpeg, and Playwright (for brand extraction from JS-rendered sites). Missing → tell the user what to install. Playwright is optional but strongly recommended — without it, brand extraction falls back to plain HTML and breaks on any modern site.

## 2. API keys — first thing, before anything else renders

If `.env` is missing but `.env.example` exists, copy it: `cp .env.example .env`. Then open `.env` and walk through keys **one at a time**. Never echo secrets back, never write values yourself — only the user fills them. Your job is to explain what each key is and where to find it.

For every key, if the user asks "was ist das" or "where do I get that", walk them through the exact click-path below. Do not skim.

### Image-generation key (optional — any one of these unlocks AI hero images)

adforge is provider-neutral. Any one of the keys below activates the hero-image pipeline. If the user already has one, use that — don't push a new signup. If they have none and want generated heroes, recommend based on what they care about:

| Key                     | Provider                       | Default model                | Get a key                                |
|-------------------------|--------------------------------|------------------------------|------------------------------------------|
| `BFL_API_KEY`           | Black Forest Labs (FLUX)       | flux-2-max                   | https://dashboard.bfl.ai/keys            |
| `GEMINI_API_KEY`        | Google Gemini / Nano Banana    | gemini-2.5-flash-image       | https://aistudio.google.com/apikey       |
| `OPENAI_API_KEY`        | OpenAI Images                  | gpt-image-1                  | https://platform.openai.com/api-keys     |
| `REPLICATE_API_TOKEN`   | Replicate (unified gateway)    | google/nano-banana-2         | https://replicate.com/account/api-tokens |
| `STABILITY_API_KEY`     | Stability AI                   | stable-image-core            | https://platform.stability.ai/account/keys |
| `FAL_KEY`               | fal.ai                         | fal-ai/flux/schnell          | https://fal.ai/dashboard/keys            |

Auto-detection order: BFL → Google → OpenAI → Replicate → Stability → fal. To force a provider regardless of which keys are set, add `IMAGE_PROVIDER=<name>` to `.env`. To change the model within a provider, set `<PROVIDER>_MODEL` (e.g. `REPLICATE_MODEL=black-forest-labs/flux-schnell`).

**If no key is set:** creatives still render — use `hero_mode: "flat_brand_color"` in variants. Fine for MVP, upgrade later.

**Bringing a provider adforge doesn't have built-in?** Invoke `image-provider-synth` — it writes a new `engines/static/image_providers/<name>.py` adapter from the provider's official docs.

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

### Fonts — done during brand setup, not later

Fonts have to land in `./fonts/` **and** have their `family` + filename entries in `brand.json.fonts` before the first render. Both engines share the same block: static (PIL) loads filenames, motion (Remotion) loads family names via `@font-face` pointing at the same TTFs. Do this now, don't defer.

While Playwright is open (you already used it for colors), read the computed `font-family` of `h1`, `body`, and the primary button. You get three candidate family names (often the same serif/sans repeated, sometimes a brand-specific display face).

Then offer the user **three paths**:

**A) "I already have the TTFs."** — Ask for the folder path. Copy the `.ttf` files into `./fonts/` at project root (create the dir if missing). Ask which file is which role (serif regular/italic, sans regular/medium/semibold, mono medium) — write names into `brand.json.fonts`. Ask for the CSS family names if the filenames don't make it obvious. If only one family is provided, reuse it for all three roles (`serif_family = sans_family = mono_family`) — it'll look homogeneous but it'll render.

**B) "Pull from my website."** — For each family name Playwright detected, try to auto-download:
  1. Check if it's a **Google Font**. The clean way: fetch `https://gwfh.mranftl.com/api/fonts/<family-id>?subsets=latin` (google-webfonts-helper — serves TTF URLs directly). The `family-id` is kebab-case lowercase (e.g. `Playfair Display` → `playfair-display`, `DM Sans` → `dm-sans`). The response is JSON with a `variants` array — each variant has a `.ttf` URL on `fonts.gstatic.com`. `curl` those into `./fonts/`. Do **not** use `fonts.googleapis.com/css2` — it returns WOFF2 even with old user-agents.
  2. Not a Google Font (custom brand face like "GT America", "Söhne", or anything proprietary) — you can't redistribute it. Tell the user: "This is a custom face we can't auto-download. Drop the TTFs into `./fonts/` and come back, or we'll use the Google defaults." Then fall through to path (C) for the roles that are still empty.
  3. Write `serif_family` / `sans_family` / `mono_family` in `brand.json.fonts` to whatever Google family you downloaded (or the custom name if the user dropped files later).

**C) "Just use the defaults."** — Download Instrument Serif (serif), Inter (sans), JetBrains Mono (mono) via the same `gwfh.mranftl.com` route (family ids: `instrument-serif`, `inter`, `jetbrains-mono`). Variants needed: regular + italic (serif), regular + 500 + 600 (sans), 500 (mono). Save TTFs as:
  - `InstrumentSerif-Regular.ttf`, `InstrumentSerif-Italic.ttf`
  - `Inter-Regular.ttf`, `Inter-Medium.ttf`, `Inter-SemiBold.ttf`
  - `JetBrainsMono-Medium.ttf`

If Playwright isn't available or you can't extract a reliable family, skip to (C) and tell the user they can swap in custom TTFs later — it's a drop-in replacement.

**Verification:** after fonts land, `ls ./fonts/` should show at least 3 files (minimum: one serif, one sans, one mono). `brand.json.fonts` should have `serif_family`, `sans_family`, `mono_family` strings plus the filename entries. If a TTF is missing at render, the static engine logs a warning and falls back to PIL's default, the motion engine falls back to the CSS generic (serif/sans-serif/monospace) — neither crashes, both render ugly. Tell the user so they know to fix it.

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

## 5. Dry-run

Compose a static creative from `variants/example.json` and a motion from `variants/ops-console-example.json`. Show the user the output files. If that works, setup is done.

Finish: "You're ready. Type 'adforge' anytime to come back to the hub."
