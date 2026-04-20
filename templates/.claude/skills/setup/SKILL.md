---
name: setup
description: First-time onboarding — brand tokens, API keys, font files, dry-run verification. Invoked from hub when state is empty or user asks for setup.
---

# setup

Onboard a new user. Everything local, no API calls until the very end.

## 1. Check runtime

Run `adforge doctor` (or the equivalent checks inline): node 18+, python3, pip, ffmpeg. Missing → tell the user what to install.

## 2. Brand

Open `brand.json`. Walk the user through customising:

- name, wordmark, domain
- colors (ink, muted, cream, accent) — accept hex or ask "paste your brand guidelines"
- voice principles (1–3 short rules)

Show the diff before writing.

## 3. Fonts

Tell the user: drop `.ttf` files into `./fonts/` matching the names in `brand.json`, or change the names in `brand.json` to match files they already have. Defaults are Google Fonts (Instrument Serif, JetBrains Mono, Inter).

## 4. API keys

Open `.env.example`, ask for values one at a time. Write `.env`. Never echo secrets back. Required:

- `BFL_API_KEY` — for hero image generation (optional, can skip)
- `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_PAGE_ID` — for deploy
- `META_PIXEL_ID` — only if using conversion-optimized adsets

## 5. Dry-run

Compose a static creative from `variants/example.json` and a motion from `variants/ops-console-example.json`. Show the user the output files. If that works, setup is done.

Finish: "You're ready. Type 'adforge' anytime to come back to the hub."
