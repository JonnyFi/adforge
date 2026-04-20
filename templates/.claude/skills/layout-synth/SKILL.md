---
name: layout-synth
description: Backend skill — read a reference ad (image or mockup) and synthesize a new static layout module under engines/static/examples/. Use when the user shows a visual example that none of the existing example layouts match.
---

# layout-synth

Turn a reference image into an executable `engines/static/examples/<name>.py`. The user shows you a creative they want adforge to make; you produce a new layout module that renders it with their `brand.json` plugged in.

Layouts in `engines/static/examples/` are *reference implementations*, not templates. Each new layout should be structurally distinct from existing ones — two brands using `advertorial` should never produce ads that look identical. If a reference is a cosmetic variant of an existing layout, extend the existing schema; don't clone.

## When to invoke

- User uploads an image or mockup and says "I want ads like this".
- Existing layouts (`advertorial`, `quote-card`, `stat-card`) don't match the structure — e.g. the reference has a big founder portrait, a before/after split, a product-photo-with-caption, a meme-style framing, a carousel-panel look, etc.

If one of the existing layouts *does* match, don't synthesize. Hand back to `composer-speccer` to draft a variant JSON against the existing layout.

## Process

### 1. Read the image

Actually look at it. Describe out loud, in the conversation:

- **Shape of the canvas**: square, portrait, story-height.
- **Vertical rhythm** top→bottom: what lives where (eyebrow? hero photo? giant number? quote? signature?). Estimate rough pixel bands.
- **Focal point**: the one thing the eye lands on first.
- **Typography**: serif headline vs sans hook? display sizes vs body sizes?
- **Color roles**: which color is brand accent, which is neutral, which is on-image?
- **Graphic elements**: rules, dividers, badges, icons, photo treatments (duotone? cutout?).

This description IS the spec. Write it down in the chat before drafting code.

### 2. Propose a name + schema

Short kebab-case name: `face-first`, `before-after`, `product-caption`, `badge-card`. Check `engines/static/examples/` — don't collide.

Draft a `SCHEMA` dict: which fields does a variant JSON need to drive this layout? Keep names consistent with existing layouts where possible (`headline`, `eyebrow`, `body`, `source`, `cta`). Only invent new field names for genuinely new content slots (`portrait_path`, `before_image`, `after_image`, `badge_text`).

Show the schema to the user and get sign-off before writing code.

### 3. Draft the layout module

Template the new file after an existing layout that's structurally nearest:

- Text-heavy, editorial → start from `advertorial.py`
- Single-sentence focal → start from `quote_card.py`
- Number-or-symbol hero → start from `stat_card.py`

Rules — non-negotiable:

- **Import only from `shared`**: `from shared import wrap_text, draw_tracked, tracked_width` and similar. Do not import PIL directly for text measurement; use the helpers.
- **Use `brand.font(role, size)`** for all typography. Roles are those defined in the user's `brand.json` (`serif_regular`, `serif_italic`, `body_regular`, `body_medium`, `body_semibold`, `mono_medium`). Never load a TTF by path.
- **Use brand colors**: `brand.ink`, `brand.muted`, `brand.accent`, `brand.cream`, `brand.highlight`. Don't hardcode hex codes. If the reference uses a color not in brand.json, ask the user whether to (a) add the color to brand.json or (b) use the closest existing role.
- **Size maps per format**: font sizes and offsets vary by aspect. Follow the `{"4x5": ..., "1x1": ..., "9x16": ...}` dict pattern from existing layouts.
- **Respect `band_h`**: if `band_h > 0`, the top of the canvas is already occupied by a hero photo (set by `hero_mode: "top_band"`). Start layout content below it.
- **Layout modules are PIL-only.** The module itself should import only `PIL` + `shared`. Keep it portable.
- **Canvas is RGB, not RGBA.** Don't call `canvas.alpha_composite(...)` — it errors with `image has wrong mode`. For soft shadows / translucent overlays, build a grayscale `L` mask, blur it, then `canvas.paste(color_layer, (x, y), mask)`. Example shadow:
  ```python
  from PIL import Image, ImageDraw, ImageFilter
  shadow_mask = Image.new("L", (w + 60, h + 60), 0)
  ImageDraw.Draw(shadow_mask).rounded_rectangle([(30, 30), (w + 30, h + 30)], radius=48, fill=90)
  shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(20))
  shadow_layer = Image.new("RGB", (w + 60, h + 60), (0, 0, 0))
  canvas.paste(shadow_layer, (x - 30, y - 20), shadow_mask)
  ```
- **Asset preprocessing is open.** If the reference needs a cutout portrait, a duotoned product shot, a generated illustration, a masked photo, etc. — do that **outside the layout** as a prep step (ad-hoc venv, rembg, Flux, Photoshop, whatever works). The layout consumes the finished PNG. Don't bake one-off capabilities into adforge core; leave the creative problem-solving open.
- **Never render the brand wordmark or logo inside a layout.** `apply_chrome` in `shared.py` handles it — brands opt in via `brand.json → chrome.wordmark` (text or image logo) and the composer calls `apply_chrome` after every layout render. If you hardcode `draw.text(..., brand.wordmark, ...)` or paste a logo image inside a layout, every brand using it gets a mark whether they want one or not, and the opt-in system breaks. Layout-integral editorial marks (domain stamps, footer rules specific to the layout's design) are fine — those aren't chrome.

Module shape:

```python
"""short docstring — what this layout communicates and when to use it."""
from PIL import ImageDraw

from shared import wrap_text, draw_tracked  # add only what you use

LAYOUT_NAME = "face-first"

SCHEMA = {
    "eyebrow": "short all-caps label",
    "portrait_path": "project-relative path to a portrait image (cutout on brand bg works best)",
    "headline": "main serif statement",
    "cta": "optional in-creative CTA",
}


def render(canvas, variant, brand, size, band_h):
    W, H = size
    fmt = variant.get("format", "4x5")
    draw = ImageDraw.Draw(canvas)
    # ... layout-specific drawing ...
```

### 4. Test-render

Write a tiny test variant at `variants/_layout-synth-test.json` using the new layout. Render once per intended format:

```
python3 engines/static/compose.py variants/_layout-synth-test.json 4x5 outputs/static/_synth-test_4x5.png
python3 engines/static/compose.py variants/_layout-synth-test.json 9x16 outputs/static/_synth-test_9x16.png
```

Show the output to the user. Iterate on pixel offsets, font sizes, and content order based on their feedback.

### 5. Hand off

Once the user approves the output:

- Delete `_layout-synth-test.json` (it was scratch).
- Tell `composer-speccer` the new layout is available and paste the `SCHEMA`.
- The layout is live — `engines/static/examples/` is auto-discovered by `compose.py` on every run.

## Rules

- **One layout per file.** Don't stuff two concepts into one module.
- **Never modify `shared.py`** unless the new layout genuinely needs a new primitive (e.g. a `draw_cutout_shadow` helper). If you do, argue for it first — "I need X because Y" — and get user sign-off.
- **Never modify existing layouts** to make the new one work. If the reference is close to an existing layout, either fork it cleanly or make the existing one parametric via SCHEMA fields.
- **Motion reference images**: if the user shows a video/animated mockup, this skill doesn't cover it. Hand off to `motion-synth` — motion compositions live in `engines/motion/src/examples/` and require Remotion/TSX, which is out of scope here.
- **No fake brand values.** If `brand.json` doesn't have a color/font the reference needs, ask the user to extend `brand.json` first, then synthesize. Don't hardcode.
