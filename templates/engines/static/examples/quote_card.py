"""quote-card — big centered serif pull-quote + attribution.

Use when a single sentence does the heavy lifting (testimonial, founder line).
"""
from PIL import ImageDraw

from shared import wrap_text

LAYOUT_NAME = "quote-card"

SCHEMA = {
    "context": "small label above the quote, e.g. 'What operators said'",
    "headline": "the quote itself, in quotation marks",
    "headline_highlight_phrase": "optional phrase inside headline to render in accent+italic",
    "headline_italic_words": "optional list of words to italicize",
    "cta": "optional — bottom-right CTA link",
}


def render(canvas, variant, brand, size, band_h):
    W, H = size
    fmt = variant.get("format", "4x5")
    pad_x = 200
    pad_bottom = 200

    if band_h > 0:
        hook_size = {"4x5": 100, "1x1": 92, "9x16": 110}[fmt]
    else:
        hook_size = {"4x5": 132, "1x1": 118, "9x16": 142}[fmt]

    serif = brand.font("serif_regular", hook_size)
    serif_italic = brand.font("serif_italic", hook_size)
    draw = ImageDraw.Draw(canvas)
    content_w = W - 2 * pad_x

    context = variant.get("context", "")
    context_size = 58
    context_font = brand.font("body_medium", context_size)
    hook = variant["headline"]
    italic_words = set(variant.get("headline_italic_words", []))
    highlight_phrase = variant.get("headline_highlight_phrase", "")
    lines = wrap_text(draw, hook, serif, content_w)
    line_h = int(hook_size * 1.04)
    block_h = line_h * len(lines) + (context_size + 64 if context else 0)

    top = band_h + 80 if band_h else int(H * 0.16)
    bot = H - pad_bottom - 260
    cursor_y = top + max(0, (bot - top - block_h) // 2)

    if context:
        draw.text((pad_x, cursor_y), context, font=context_font, fill=brand.muted)
        cursor_y += context_size + 64

    highlight_ids = set()
    if highlight_phrase:
        all_w = hook.split()
        tgt = highlight_phrase.split()
        for i in range(len(all_w) - len(tgt) + 1):
            if all(all_w[i + j].strip(".,:;!?\"'„“”‚‘’").lower() == tgt[j].strip(".,:;!?\"'„“”‚‘’").lower() for j in range(len(tgt))):
                highlight_ids.update(range(i, i + len(tgt)))
                break

    global_idx = 0
    for line in lines:
        x = pad_x
        words = line.split(" ")
        for i, word in enumerate(words):
            strip = word.strip(".,:;!?\"'„“”‚‘’")
            is_hl = global_idx in highlight_ids
            f = serif_italic if (strip in italic_words or is_hl) else serif
            fill = brand.accent if is_hl else brand.ink
            draw.text((x, cursor_y), word, font=f, fill=fill)
            bbox = draw.textbbox((0, 0), word + (" " if i < len(words) - 1 else ""), font=f)
            x += bbox[2] - bbox[0]
            global_idx += 1
        cursor_y += line_h

    cta_font = brand.font("body_medium", 50)
    stamp_y = H - pad_bottom - 40
    cta = variant.get("cta", "").strip() if variant.get("cta") else ""
    if cta:
        cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
        cta_w = cta_bbox[2] - cta_bbox[0]
        cta_x = W - pad_x - cta_w
        cta_y = stamp_y + 16
        draw.text((cta_x, cta_y), cta, font=cta_font, fill=brand.accent)
        ul_y = cta_y + (cta_bbox[3] - cta_bbox[1]) + 6
        draw.line([(cta_x, ul_y), (cta_x + cta_w, ul_y)], fill=brand.accent, width=3)
