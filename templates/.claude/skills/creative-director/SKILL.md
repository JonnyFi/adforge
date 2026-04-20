---
name: creative-director
description: Backend skill — propose ad angles with hooks, body, CTA drafts. Used by new-campaign and add-creative, not invoked directly by end users.
---

# creative-director

Translate a rough user brief into 3 concrete ad angles.

## Input

- The user's one-sentence brief
- Target audience description
- `brand.json` voice principles and audience

## Output

Present 3 angles. Each has:

- **Angle name** (1–3 words)
- **Hook** (one sentence, max 14 words, concrete and specific)
- **Body draft** (2–3 sentences for static ads, short sentence list for motion)
- **CTA** (2–4 words)
- **Suggested format** (static + layout, or motion + composition)

Variety across the three:
- one problem-framed (pain)
- one outcome-framed (proof/result)
- one voice-framed (quote/testimonial)

## Rules

- Plain language. No "revolutionary", "seamless", "game-changing".
- Specific numbers over adjectives where possible.
- Match the brand's `voice.principles` — re-check before returning.
- User's verbatim phrases from the brief beat your rewrites. If they said "30 minutes", don't soften to "fast".
- If the user's locale needs it, stay in their language. Never translate unless asked.

After presenting, ask which angle to go with (number or "iterate on X").
