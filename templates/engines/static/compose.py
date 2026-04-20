#!/usr/bin/env python3
"""adforge static composer — PIL pipeline for print-style ad creatives.

Reads a variant JSON + brand.json, writes a PNG.

Usage:
    python3 engines/static/compose.py <variant.json> <format> <out.png>

Layouts (variant.layout):
    advertorial  — eyebrow + accent rule + serif headline + body lede + CTA
    quote-card   — big centered serif pull-quote + attribution
    stat-card    — oversized number + label + supporting line + source
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Brand:
    def __init__(self, data, root):
        self.data = data
        self.root = root
        c = data["colors"]
        self.ink = hex_to_rgb(c["ink"])
        self.muted = hex_to_rgb(c["muted"])
        self.cream = hex_to_rgb(c["cream"])
        self.cream_alt = hex_to_rgb(c.get("cream_alt", c["cream"]))
        self.accent = hex_to_rgb(c["accent"])
        self.highlight = hex_to_rgb(c.get("highlight", c["accent"]))
        self.wordmark = data.get("wordmark", data.get("name", ""))
        self.domain = data.get("domain", "")
        fonts = data["fonts"]
        font_dir = Path(fonts["dir"])
        if not font_dir.is_absolute():
            font_dir = root / font_dir
        self.font_dir = font_dir
        self.font_files = fonts
        self.radiant = data.get("radiant_gradient")

    def font(self, role, size):
        fname = self.font_files[role]
        return ImageFont.truetype(str(self.font_dir / fname), size=size)


# --- text utilities -------------------------------------------------------


def wrap_text(draw, text, font, max_width):
    lines, current = [], ""
    for w in text.split(" "):
        trial = (current + " " + w).strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def draw_tracked(draw, xy, text, font, fill, tracking_em):
    x, y = xy
    track_px = int(font.size * tracking_em)
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), ch, font=font)
        x += (bbox[2] - bbox[0]) + track_px


def tracked_width(draw, text, font, tracking_em):
    track_px = int(font.size * tracking_em)
    total = 0
    for ch in text:
        bbox = draw.textbbox((0, 0), ch, font=font)
        total += (bbox[2] - bbox[0]) + track_px
    return max(0, total - track_px)


# --- image utilities ------------------------------------------------------


def crop_cover(img, target_w, target_h, bias_y=0.5, bias_x=0.5):
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    dst_ratio = target_w / target_h
    if src_ratio > dst_ratio:
        new_w = int(src_h * dst_ratio)
        offset = int((src_w - new_w) * bias_x)
        img = img.crop((offset, 0, offset + new_w, src_h))
    else:
        new_h = int(src_w / dst_ratio)
        offset = int((src_h - new_h) * bias_y)
        img = img.crop((0, offset, src_w, offset + new_h))
    return img.resize((target_w, target_h), Image.LANCZOS)


def build_radiant_gradient(size, radiant):
    W, H = size
    top = tuple(radiant["top_color"])
    bot = tuple(radiant["bottom_color"])
    canvas = Image.new("RGB", (W, H), bot)
    d = ImageDraw.Draw(canvas)
    for y in range(H):
        t = y / max(1, H - 1)
        k = min(1.0, t / 0.60)
        r = int(top[0] + (bot[0] - top[0]) * k)
        g = int(top[1] + (bot[1] - top[1]) * k)
        b = int(top[2] + (bot[2] - top[2]) * k)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    canvas = canvas.convert("RGBA")
    for stop in radiant["stops"]:
        rx = int(W * stop["ellipse_w"] * stop["fade"] * 0.5)
        ry = int(H * stop["ellipse_h"] * stop["fade"] * 0.5)
        cx = int(W * stop["cx"])
        cy = int(H * stop["cy"])
        peak = int(255 * stop["opacity"])
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        steps = 72
        for i in range(steps):
            t = i / (steps - 1)
            alpha = int(peak * (t ** 1.8))
            scale = 1.0 - t
            erx = int(rx * scale)
            ery = int(ry * scale)
            if erx <= 1 or ery <= 1:
                continue
            md.ellipse([cx - erx, cy - ery, cx + erx, cy + ery], fill=alpha)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=max(rx, ry) * 0.04))
        layer = Image.new("RGBA", (W, H), tuple(stop["color"]) + (255,))
        layer.putalpha(mask)
        canvas = Image.alpha_composite(canvas, layer)
    return canvas.convert("RGB")


def build_readability_halo(size, brand, strength=0.85):
    W, H = size
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = W // 2, int(H * 0.58)
    rx = int(W * 0.78)
    ry = int(H * 0.58)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=int(255 * strength))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=180))
    layer = Image.new("RGBA", (W, H), brand.cream + (255,))
    layer.putalpha(mask)
    return layer


def base_canvas(size, variant, brand):
    hero_mode = variant.get("hero_mode", "flat_brand_color")
    hero_path = variant.get("hero_image")
    if hero_path and not Path(hero_path).is_absolute():
        hero_path = str(Path.cwd() / hero_path)
    W, H = size
    canvas = Image.new("RGB", (W, H), brand.cream)
    band_h = 0
    # flat_brand_color leaves the default cream fill alone — no-op branch
    if hero_mode == "background" and hero_path:
        bg = Image.open(hero_path).convert("RGB")
        canvas = crop_cover(bg, W, H)
        halo = build_readability_halo((W, H), brand, strength=0.88)
        canvas = canvas.convert("RGBA")
        canvas.alpha_composite(halo)
        canvas = canvas.convert("RGB")
    elif hero_mode == "radiant_gradient":
        canvas = build_radiant_gradient((W, H), brand.radiant)
    elif hero_mode == "top_band" and hero_path:
        fmt = variant.get("format", "4x5")
        top_pct = {"4x5": 0.52, "1x1": 0.50, "9x16": 0.55}.get(fmt, 0.50)
        band_h = int(H * top_pct)
        focal_y = variant.get("hero_focal_y", 0.28)
        photo = Image.open(hero_path).convert("RGB")
        photo = crop_cover(photo, W, band_h, bias_y=focal_y)
        canvas.paste(photo, (0, 0))
        grad = Image.new("L", (W, 80), 0)
        gd = ImageDraw.Draw(grad)
        for i in range(80):
            gd.line([(0, i), (W, i)], fill=int(255 * (i / 79)))
        strip = Image.new("RGBA", (W, 80), brand.cream + (255,))
        strip.putalpha(grad)
        canvas = canvas.convert("RGBA")
        canvas.alpha_composite(strip, (0, band_h - 40))
        canvas = canvas.convert("RGB")

    # subtle paper grain
    noise = Image.effect_noise((W, H), 4).convert("RGB")
    noise = noise.filter(ImageFilter.GaussianBlur(radius=1.5))
    canvas = Image.blend(canvas, noise, alpha=0.03)
    return canvas, band_h


# --- layouts --------------------------------------------------------------


def layout_advertorial(canvas, variant, brand, size, band_h):
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

    # eyebrow
    eyebrow = variant["eyebrow"].upper()
    draw_tracked(draw, (pad_x, cursor_y), eyebrow, eyebrow_font, brand.muted, 0.18)
    cursor_y += eyebrow_size + 72
    draw.line([(pad_x, cursor_y), (pad_x + 160, cursor_y)], fill=brand.accent, width=4)
    cursor_y += 84

    # headline
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

    # body with optional bold dateline
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

    # CTA (opt-in only — Meta's platform CTA button is primary)
    cta = variant.get("cta", "").strip() if variant.get("cta") else ""
    if cta:
        cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
        cta_w = cta_bbox[2] - cta_bbox[0]
        draw.text((pad_x, cursor_y), cta, font=cta_font, fill=brand.accent)
        ul_y = cursor_y + (cta_bbox[3] - cta_bbox[1]) + 8
        draw.line([(pad_x, ul_y), (pad_x + cta_w, ul_y)], fill=brand.accent, width=4)
        cursor_y += cta_size + 64

    # byline / colophon
    byline = variant.get("byline")
    if byline:
        draw.text((pad_x, H - pad_bottom - byline_size), byline, font=byline_font, fill=brand.muted)

    # bottom signature when the lower canvas is otherwise empty (flat / gradient)
    if variant.get("hero_mode", "flat_brand_color") in ("flat_brand_color", "radiant_gradient") and brand.wordmark:
        mono_small = brand.font("mono_medium", 36)
        wordmark_font = brand.font("serif_italic", 72)
        rule_y = H - pad_bottom - 120
        draw.line([(pad_x, rule_y), (W - pad_x, rule_y)], fill=brand.muted, width=2)
        draw.text((pad_x, rule_y + 24), brand.wordmark, font=wordmark_font, fill=brand.accent)
        if brand.domain:
            right = brand.domain.upper()
            right_w = tracked_width(draw, right, mono_small, 0.22)
            draw_tracked(draw, (W - pad_x - right_w, rule_y + 46), right, mono_small, brand.muted, 0.22)


def layout_quote_card(canvas, variant, brand, size, band_h):
    """Big serif pull-quote, optional hero top band, attribution bottom."""
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

    # compute highlight-word set
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

    # brand stamp + cta
    wordmark_font = brand.font("serif_italic", 64)
    cta_font = brand.font("body_medium", 50)
    stamp_y = H - pad_bottom - 40
    if brand.wordmark:
        draw.text((pad_x, stamp_y), brand.wordmark, font=wordmark_font, fill=brand.accent)
    cta = variant.get("cta", "").strip() if variant.get("cta") else ""
    if cta:
        cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
        cta_w = cta_bbox[2] - cta_bbox[0]
        cta_x = W - pad_x - cta_w
        cta_y = stamp_y + 16
        draw.text((cta_x, cta_y), cta, font=cta_font, fill=brand.accent)
        ul_y = cta_y + (cta_bbox[3] - cta_bbox[1]) + 6
        draw.line([(cta_x, ul_y), (cta_x + cta_w, ul_y)], fill=brand.accent, width=3)


def layout_stat_card(canvas, variant, brand, size, band_h):
    """Oversized number with label + supporting line + source."""
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

    # eyebrow optional at top
    eyebrow = variant.get("eyebrow", "").upper()
    eyebrow_font = brand.font("mono_medium", 44)
    cursor_y = int(H * 0.18)
    if eyebrow:
        draw_tracked(draw, (pad_x, cursor_y), eyebrow, eyebrow_font, brand.muted, 0.18)
        cursor_y += 44 + 60

    # the number
    number = variant.get("number", variant.get("headline", "42"))
    nbbox = draw.textbbox((0, 0), number, font=number_font)
    draw.text((pad_x, cursor_y), number, font=number_font, fill=brand.accent)
    cursor_y += (nbbox[3] - nbbox[1]) + 40

    # label
    label = variant.get("label", variant.get("body", ""))
    for line in wrap_text(draw, label, label_font, content_w):
        draw.text((pad_x, cursor_y), line, font=label_font, fill=brand.ink)
        cursor_y += int(label_size * 1.2)
    cursor_y += 40

    # support line
    support = variant.get("support", "")
    if support:
        for line in wrap_text(draw, support, support_font, content_w):
            draw.text((pad_x, cursor_y), line, font=support_font, fill=brand.muted)
            cursor_y += int(support_size * 1.4)

    # source bottom
    source = variant.get("source", "")
    if source:
        sbbox = draw.textbbox((0, 0), source, font=source_font)
        draw.text((pad_x, H - pad_bottom - (sbbox[3] - sbbox[1])), source, font=source_font, fill=brand.muted)

    # colophon
    if brand.wordmark:
        wordmark_font = brand.font("serif_italic", 64)
        wm_bbox = draw.textbbox((0, 0), brand.wordmark, font=wordmark_font)
        wm_w = wm_bbox[2] - wm_bbox[0]
        draw.text((W - pad_x - wm_w, H - pad_bottom - 40 - (wm_bbox[3] - wm_bbox[1])),
                  brand.wordmark, font=wordmark_font, fill=brand.accent)


LAYOUTS = {
    "advertorial": layout_advertorial,
    "quote-card": layout_quote_card,
    "stat-card": layout_stat_card,
}


# --- main -----------------------------------------------------------------


FORMATS = {
    "1x1": (2160, 2160),
    "4x5": (2160, 2700),
    "9x16": (2160, 3840),
}


def find_project_root(start):
    """Walk up from variant file to find adforge.config.json."""
    p = Path(start).resolve()
    for parent in [p.parent, *p.parents]:
        if (parent / "adforge.config.json").exists():
            return parent
    raise SystemExit("error: no adforge.config.json found — is this inside an adforge project?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant", help="path to variant JSON")
    ap.add_argument("format", choices=list(FORMATS), help="output format (1x1, 4x5, 9x16)")
    ap.add_argument("out", help="output PNG path")
    ap.add_argument("--brand", help="override brand.json path")
    args = ap.parse_args()

    variant_path = Path(args.variant)
    root = find_project_root(variant_path)
    brand_path = Path(args.brand) if args.brand else root / "brand.json"
    brand = Brand(json.loads(brand_path.read_text()), root)
    variant = json.loads(variant_path.read_text())
    variant["format"] = args.format

    layout_name = variant.get("layout", "advertorial")
    if layout_name not in LAYOUTS:
        raise SystemExit(f"error: unknown layout '{layout_name}'. available: {list(LAYOUTS)}")

    size = FORMATS[args.format]
    canvas, band_h = base_canvas(size, variant, brand)
    LAYOUTS[layout_name](canvas, variant, brand, size, band_h)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG", optimize=True)
    print(f"wrote {out} ({size[0]}x{size[1]}, layout={layout_name})")


if __name__ == "__main__":
    main()
