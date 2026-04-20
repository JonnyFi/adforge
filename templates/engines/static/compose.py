#!/usr/bin/env python3
"""adforge static composer — thin dispatcher over the layout registry.

Reads a variant JSON + brand.json, picks the layout named in variant.layout,
writes a PNG.

Usage:
    python3 engines/static/compose.py <variant.json> <format> <out.png>

Layouts live in `engines/static/layouts/`. Drop a new module there (must export
LAYOUT_NAME + render) and it's immediately available — no edits here.
"""
import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from shared import Brand, FORMATS, base_canvas, find_project_root  # noqa: E402
from layouts import discover  # noqa: E402


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

    registry = discover()
    layout_name = variant.get("layout", "advertorial")
    if layout_name not in registry:
        raise SystemExit(f"error: unknown layout '{layout_name}'. available: {sorted(registry)}")

    size = FORMATS[args.format]
    canvas, band_h = base_canvas(size, variant, brand)
    registry[layout_name](canvas, variant, brand, size, band_h)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG", optimize=True)
    print(f"wrote {out} ({size[0]}x{size[1]}, layout={layout_name})")


if __name__ == "__main__":
    main()
