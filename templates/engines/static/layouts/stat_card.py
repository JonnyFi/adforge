"""stat-card — oversized number + label + support line + source.

Use when a single hard number carries the story. Numbers without a source
field should be refused by composer-speccer — no made-up stats.
"""
from PIL import ImageDraw

from shared import wrap_text, draw_tracked

LAYOUT_NAME = "stat-card"

SCHEMA = {
    "eyebrow": "optional all-caps label at top",
    "number": "the headline stat (e.g. '83%', '3x', '€2.4M')",
    "label": "what the number means (1–2 lines)",
    "support": "optional supporting sentence below the label",
    "source": "where the number comes from — REQUIRED, no unsourced stats",
}


def render(canvas, variant, brand, size, band_h):
    W, H = size
    fmt = variant.get("format", "4x5")
    pad_x = 180
    pad_bottom = 176

    number_size = {"4x5": 500, "1x1": 440, "9x16": 560}[fmt]
    label_size = 72
    support_size = 56
    source_size = 40

    number_font = brand.font("serif_regular", number_size)
    label_font = brand.font("body_semibold", label_size)
    support_font = brand.font("body_regular", support_size)
    source_font = brand.font("mono_medium", source_size)

    draw = ImageDraw.Draw(canvas)
    content_w = W - 2 * pad_x

    eyebrow = variant.get("eyebrow", "").upper()
    eyebrow_font = brand.font("mono_medium", 44)
    cursor_y = int(H * 0.18)
    if eyebrow:
        draw_tracked(draw, (pad_x, cursor_y), eyebrow, eyebrow_font, brand.muted, 0.18)
        cursor_y += 44 + 60

    number = variant.get("number", variant.get("headline", "42"))
    nbbox = draw.textbbox((0, 0), number, font=number_font)
    draw.text((pad_x, cursor_y), number, font=number_font, fill=brand.accent)
    cursor_y += (nbbox[3] - nbbox[1]) + 40

    label = variant.get("label", variant.get("body", ""))
    for line in wrap_text(draw, label, label_font, content_w):
        draw.text((pad_x, cursor_y), line, font=label_font, fill=brand.ink)
        cursor_y += int(label_size * 1.2)
    cursor_y += 40

    support = variant.get("support", "")
    if support:
        for line in wrap_text(draw, support, support_font, content_w):
            draw.text((pad_x, cursor_y), line, font=support_font, fill=brand.muted)
            cursor_y += int(support_size * 1.4)

    source = variant.get("source", "")
    if source:
        sbbox = draw.textbbox((0, 0), source, font=source_font)
        draw.text((pad_x, H - pad_bottom - (sbbox[3] - sbbox[1])), source, font=source_font, fill=brand.muted)

    if brand.wordmark:
        wordmark_font = brand.font("serif_italic", 64)
        wm_bbox = draw.textbbox((0, 0), brand.wordmark, font=wordmark_font)
        wm_w = wm_bbox[2] - wm_bbox[0]
        draw.text((W - pad_x - wm_w, H - pad_bottom - 40 - (wm_bbox[3] - wm_bbox[1])),
                  brand.wordmark, font=wordmark_font, fill=brand.accent)
