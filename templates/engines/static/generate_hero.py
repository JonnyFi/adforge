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
import inspect
import os
import sys
from pathlib import Path

PROVIDERS_DIR = Path(__file__).parent / "image_providers"

# Magic-byte signatures for the image formats any provider may legitimately
# return. If the bytes we got back don't match, the provider handed us an
# error payload, HTML, or truncated response — surface it immediately rather
# than writing a broken file to disk.
_IMAGE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"\xff\xd8\xff",      "JPEG"),
    (b"GIF87a",            "GIF"),
    (b"GIF89a",            "GIF"),
    # WebP: "RIFF....WEBP" — prefix + offset 8 check handled separately.
]

_VALID_EXTS_FOR_FORMAT: dict[str, set[str]] = {
    "PNG":  {".png"},
    "JPEG": {".jpg", ".jpeg"},
    "GIF":  {".gif"},
    "WebP": {".webp"},
}
_CANONICAL_EXT_FOR_FORMAT: dict[str, str] = {
    "PNG": ".png", "JPEG": ".jpg", "GIF": ".gif", "WebP": ".webp",
}


def _detect_format(data: bytes) -> str | None:
    for sig, name in _IMAGE_SIGNATURES:
        if data.startswith(sig):
            return name
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WebP"
    return None

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
    try:
        sig = inspect.signature(module.generate)
        params = list(sig.parameters.values())
    except (TypeError, ValueError):
        params = None
    if params is not None:
        required = [p for p in params if p.default is inspect.Parameter.empty
                    and p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                   inspect.Parameter.POSITIONAL_OR_KEYWORD)]
        if len(required) != 3:
            raise RuntimeError(
                f"Provider {name!r} generate() must accept exactly 3 required args "
                f"(prompt, width, height); got {len(required)}. "
                f"See engines/static/image_providers/CONTRACT.md."
            )
    return module


def generate_hero(prompt: str, width: int, height: int, provider: str | None = None) -> bytes:
    """Programmatic entry point — pick a provider and return image bytes."""
    name = provider or pick_provider()
    module = load_provider(name)
    data = module.generate(prompt, width, height)
    if not isinstance(data, (bytes, bytearray)):
        raise RuntimeError(
            f"Provider {name!r} returned {type(data).__name__}; "
            f"CONTRACT.md requires bytes."
        )
    if _detect_format(bytes(data)) is None:
        head = bytes(data[:8]).hex()
        raise RuntimeError(
            f"Provider {name!r} returned {len(data)} bytes that are not PNG/JPEG/GIF/WebP "
            f"(first 8 bytes: {head}). Likely an error payload or truncated response."
        )
    return bytes(data)


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
    except Exception as e:  # noqa: BLE001 — surface type only; provider contract
        _eprint(f"[generate_hero] unexpected {type(e).__name__} from {name!r} — see CONTRACT.md")
        return 1

    # Ensure the output path's extension matches the actual image format.
    # Providers may legitimately return JPEG when the caller asked for PNG;
    # writing JPEG bytes to a .png path leaves downstream tools (Meta upload,
    # PIL Image.open, file(1)) to cope with a lying extension.
    fmt = _detect_format(image_bytes)
    if fmt and output_path.suffix.lower() not in _VALID_EXTS_FOR_FORMAT.get(fmt, set()):
        new_path = output_path.with_suffix(_CANONICAL_EXT_FOR_FORMAT[fmt])
        _eprint(
            f"[generate_hero] provider returned {fmt} but output path was "
            f"{output_path.name} — writing to {new_path.name} instead"
        )
        output_path = new_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)
    _eprint(f"[generate_hero] saved {output_path} ({len(image_bytes)} bytes)")
    # Print the final path on stdout so callers can capture it — extension
    # may differ from what they requested if the provider returned a
    # different format.
    print(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
