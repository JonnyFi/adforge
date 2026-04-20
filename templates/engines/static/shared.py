"""Shared primitives for adforge static layouts.

Every layout module under `layouts/` imports from here. This file owns:
    - Brand (color + font loader)
    - text helpers (wrap_text, draw_tracked, tracked_width)
    - image helpers (crop_cover, build_radiant_gradient, build_readability_halo)
    - base_canvas (hero_mode dispatch + paper grain)
    - FORMATS (canvas sizes per aspect)

Layouts receive (canvas, variant, brand, size, band_h) and draw on the canvas.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter


FORMATS = {
    "1x1": (2160, 2160),
    "4x5": (2160, 2700),
    "9x16": (2160, 3840),
}


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

    noise = Image.effect_noise((W, H), 4).convert("RGB")
    noise = noise.filter(ImageFilter.GaussianBlur(radius=1.5))
    canvas = Image.blend(canvas, noise, alpha=0.03)
    return canvas, band_h


def find_project_root(start):
    p = Path(start).resolve()
    for parent in [p.parent, *p.parents]:
        if (parent / "adforge.config.json").exists():
            return parent
    raise SystemExit("error: no adforge.config.json found — is this inside an adforge project?")
