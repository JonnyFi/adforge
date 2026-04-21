#!/usr/bin/env python3
"""
Image-generation dispatcher.

Usage (shell):
    python3 engines/static/generate_hero.py <output_path> <width> <height> <<<"prompt text"

Provider selection:
    1. If IMAGE_PROVIDER is set, use that.
    2. Otherwise, auto-detect from the first present API key in this order:
       BFL_API_KEY, GEMINI_API_KEY (or GOOGLE_AI_STUDIO_API_KEY),
       OPENAI_API_KEY, REPLICATE_API_TOKEN, STABILITY_API_KEY, FAL_KEY.
    3. If nothing matches, exit with a clear hint about IMAGE_PROVIDER and the
       hero_mode: "flat_brand_color" fallback.

Provider modules live under engines/static/image_providers/. See CONTRACT.md
there for the interface. Drop a new <name>.py to add a provider; the dispatcher
picks it up automatically via IMAGE_PROVIDER=<name>.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

PROVIDERS_DIR = Path(__file__).parent / "image_providers"

# Auto-detect order. First match wins. Keep in sync with CONTRACT.md + README.
DETECTION_ORDER = [
    ("bfl",       ["BFL_API_KEY"]),
    ("google",    ["GEMINI_API_KEY", "GOOGLE_AI_STUDIO_API_KEY"]),
    ("openai",    ["OPENAI_API_KEY"]),
    ("replicate", ["REPLICATE_API_TOKEN"]),
    ("stability", ["STABILITY_API_KEY"]),
    ("fal",       ["FAL_KEY"]),
]


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def list_providers() -> list[str]:
    """Return every provider module name found on disk (built-in + user-dropped)."""
    if not PROVIDERS_DIR.is_dir():
        return []
    return sorted(
        p.stem for p in PROVIDERS_DIR.glob("*.py")
        if p.stem != "__init__" and not p.stem.startswith("_")
    )


def pick_provider() -> str:
    """Resolve which provider to use. Raises RuntimeError if none."""
    explicit = os.environ.get("IMAGE_PROVIDER", "").strip()
    available = list_providers()

    if explicit:
        if explicit not in available:
            raise RuntimeError(
                f"IMAGE_PROVIDER={explicit!r} is set but no module "
                f"engines/static/image_providers/{explicit}.py was found. "
                f"Available: {', '.join(available) or '(none)'}."
            )
        return explicit

    for name, keys in DETECTION_ORDER:
        if name not in available:
            continue
        if any(os.environ.get(k) for k in keys):
            return name

    raise RuntimeError(
        "No image provider could be auto-detected.\n"
        "Either set IMAGE_PROVIDER=<name> and the matching API key, or set one of:\n"
        "  BFL_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY, REPLICATE_API_TOKEN, "
        "STABILITY_API_KEY, FAL_KEY.\n"
        "Without any key you can still render creatives — use "
        "hero_mode: \"flat_brand_color\" in your variant."
    )


def load_provider(name: str):
    """Import the provider module from disk. Works for built-in and user-dropped adapters."""
    module_path = PROVIDERS_DIR / f"{name}.py"
    if not module_path.is_file():
        raise RuntimeError(f"Provider module not found: {module_path}")

    spec = importlib.util.spec_from_file_location(
        f"adforge_image_providers.{name}", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to build import spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "generate"):
        raise RuntimeError(
            f"Provider {name!r} does not define generate(prompt, width, height). "
            f"See engines/static/image_providers/CONTRACT.md."
        )
    return module


def generate_hero(prompt: str, width: int, height: int, provider: str | None = None) -> bytes:
    """Programmatic entry point — pick a provider and return image bytes."""
    name = provider or pick_provider()
    module = load_provider(name)
    return module.generate(prompt, width, height)


def main() -> int:
    if len(sys.argv) < 4:
        _eprint("usage: generate_hero.py <output_path> <width> <height> <<<PROMPT")
        return 2

    output_path = Path(sys.argv[1])
    try:
        width = int(sys.argv[2])
        height = int(sys.argv[3])
    except ValueError:
        _eprint("width and height must be integers")
        return 2

    prompt = sys.stdin.read().strip()
    if not prompt:
        _eprint("prompt is empty (read from stdin)")
        return 2

    try:
        name = pick_provider()
    except RuntimeError as e:
        _eprint(f"[generate_hero] {e}")
        return 1

    _eprint(f"[generate_hero] provider={name} size={width}x{height} out={output_path}")

    try:
        image_bytes = generate_hero(prompt, width, height, provider=name)
    except RuntimeError as e:
        _eprint(f"[generate_hero] provider {name!r} failed: {e}")
        return 1
    except Exception as e:  # noqa: BLE001 — surface anything providers leak
        _eprint(f"[generate_hero] unexpected error from {name!r}: {e}")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)
    _eprint(f"[generate_hero] saved {output_path} ({len(image_bytes)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
