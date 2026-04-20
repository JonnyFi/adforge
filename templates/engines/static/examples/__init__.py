"""Layout registry — auto-discovers every module in this directory.

These are EXAMPLE layouts — reference implementations, not templates. The
product is `shared.py` (primitives) + the `layout-synth` skill that writes
new layout modules per brand. Treat the files here as starting points to
copy, diverge from, or ignore.

Each module must export:
    LAYOUT_NAME:  str       — public name used in variant.layout
    render:       callable  — (canvas, variant, brand, size, band_h) -> None

Optional:
    SCHEMA:       dict      — fields the layout consumes from variant JSON.
                              Used by composer-speccer and layout-synth.

Drop a new file into this directory, set LAYOUT_NAME + render, and it's live —
no edits to compose.py needed.
"""
import importlib
import pkgutil


def discover():
    """Return {layout_name: render_fn} by importing every sibling module."""
    registry = {}
    for mod_info in pkgutil.iter_modules(__path__):
        if mod_info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{__name__}.{mod_info.name}")
        name = getattr(mod, "LAYOUT_NAME", None)
        render = getattr(mod, "render", None)
        if name and render:
            registry[name] = render
    return registry
