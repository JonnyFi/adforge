"""advertorial — Fachartikel feel: eyebrow + accent rule + serif headline + body lede.

REFERENCE IMPLEMENTATION. Read this to understand the `shared` primitives
and the layout module contract — do not reuse as-is for a new brand. If a
brief structurally fits an editorial/article feel, composer-speccer can
point a new variant at `"layout": "advertorial"`; if the brief calls for
something structurally different (portrait-first, before/after, full-bleed,
meme-frame, …), invoke `layout-synth` to write a new module.

Performs well in mid-funnel B2B placements where trust > impulse.
"""
from PIL import ImageDraw

from shared import wrap_text, draw_tracked, tracked_width

LAYOUT_NAME = "advertorial"

SCHEMA = {
    "eyebrow": "short all-caps label, e.g. 'Case Study' or 'Feature'",
    "headline": "main serif headline — one or two sentences",
    "headline_italic_words": "optional list of words inside the headline to italicize",
    "dateline": "optional bold opener in body, e.g. 'VIENNA —'",
    "body": "lede paragraph (3–5 lines)",
    "cta": "optional in-creative CTA (Meta platform button already exists)",
    "byline": "optional author/attribution line",
}


def render(canvas, variant, brand, size, band_h):
    W, H = size
    fmt = variant.get("format", "4x5")
    pad_x = 180
    pad_bottom = 176
    is_top_band = band_h > 0

    eyebrow_size = 44 if is_top_band else 48
    if is_top_band:
        headline_size = {"4x5": 148, "1x1": 140, "9x16": 168}[fmt]
    else:
        headline_size = {"4x5": 192, "1x1": 168, "9x16": 208}[fmt]
    body_size = 56 if is_top_band else 64
    byline_size = 44
    cta_size = 56 if is_top_band else 60

    eyebrow_font = brand.font("mono_medium", eyebrow_size)
    serif = brand.font("serif_regular", headline_size)
    serif_italic = brand.font("serif_italic", headline_size)
    body_font = brand.font("body_regular", body_size)
    body_bold = brand.font("body_semibold", body_size)
    byline_font = brand.font("body_regular", byline_size)
    cta_font = brand.font("body_medium", cta_size)

    draw = ImageDraw.Draw(canvas)
    content_w = W - 2 * pad_x
    if is_top_band:
        top_pct = {"4x5": 0.52, "1x1": 0.50, "9x16": 0.55}[fmt]
        cursor_y = int(H * top_pct) + 90
    else:
        cursor_y = int(H * 0.16) if fmt == "9x16" else 192

    eyebrow = variant["eyebrow"].upper()
    draw_tracked(draw, (pad_x, cursor_y), eyebrow, eyebrow_font, brand.muted, 0.18)
    cursor_y += eyebrow_size + 72
    draw.line([(pad_x, cursor_y), (pad_x + 160, cursor_y)], fill=brand.accent, width=4)
    cursor_y += 84

    italic_words = set(variant.get("headline_italic_words", []))
    lines = wrap_text(draw, variant["headline"], serif, content_w)
    line_h = int(headline_size * 1.02)
    for line in lines:
        x = pad_x
        words = line.split(" ")
        for i, word in enumerate(words):
            strip = word.strip(".,:;!?\"'„“”‚‘’")
            f = serif_italic if strip in italic_words else serif
            draw.text((x, cursor_y), word, font=f, fill=brand.ink)
            bbox = draw.textbbox((0, 0), word + (" " if i < len(words) - 1 else ""), font=f)
            x += bbox[2] - bbox[0]
        cursor_y += line_h
    cursor_y += 88

    dateline = variant.get("dateline", "").strip()
    body = variant.get("body", "")
    body_lh = int(body_size * 1.42)
    if dateline and body.startswith(dateline):
        remainder = body[len(dateline):].lstrip()
        prefix_bbox = draw.textbbox((0, 0), dateline, font=body_bold)
        prefix_w = prefix_bbox[2] - prefix_bbox[0]
        gap = 16
        words = remainder.split(" ")
        lines, current, max_w = [], "", content_w - prefix_w - gap
        for w in words:
            trial = (current + " " + w).strip()
            bbox = draw.textbbox((0, 0), trial, font=body_font)
            if bbox[2] - bbox[0] <= max_w or not current:
                current = trial
            else:
                lines.append(current)
                current = w
                max_w = content_w
        if current:
            lines.append(current)
        draw.text((pad_x, cursor_y), dateline, font=body_bold, fill=brand.ink)
        if lines:
            draw.text((pad_x + prefix_w + gap, cursor_y), lines[0], font=body_font, fill=brand.ink)
            for line in lines[1:]:
                cursor_y += body_lh
                draw.text((pad_x, cursor_y), line, font=body_font, fill=brand.ink)
            cursor_y += body_lh
    elif body:
        for line in wrap_text(draw, body, body_font, content_w):
            draw.text((pad_x, cursor_y), line, font=body_font, fill=brand.ink)
            cursor_y += body_lh
    cursor_y += 40

    cta = variant.get("cta", "").strip() if variant.get("cta") else ""
    if cta:
        cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
        cta_w = cta_bbox[2] - cta_bbox[0]
        draw.text((pad_x, cursor_y), cta, font=cta_font, fill=brand.accent)
        ul_y = cursor_y + (cta_bbox[3] - cta_bbox[1]) + 8
        draw.line([(pad_x, ul_y), (pad_x + cta_w, ul_y)], fill=brand.accent, width=4)
        cursor_y += cta_size + 64

    byline = variant.get("byline")
    if byline:
        draw.text((pad_x, H - pad_bottom - byline_size), byline, font=byline_font, fill=brand.muted)

    if variant.get("hero_mode", "flat_brand_color") in ("flat_brand_color", "radiant_gradient") and brand.domain:
        mono_small = brand.font("mono_medium", 36)
        rule_y = H - pad_bottom - 120
        draw.line([(pad_x, rule_y), (W - pad_x, rule_y)], fill=brand.muted, width=2)
        right = brand.domain.upper()
        right_w = tracked_width(draw, right, mono_small, 0.22)
        draw_tracked(draw, (W - pad_x - right_w, rule_y + 46), right, mono_small, brand.muted, 0.22)
