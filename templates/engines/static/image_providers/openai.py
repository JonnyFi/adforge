"""
OpenAI Images API — gpt-image-1.

Docs: https://platform.openai.com/docs/api-reference/images/create
      https://platform.openai.com/docs/guides/image-generation
Verified: 2026-04-20

Env:
    OPENAI_API_KEY    required — https://platform.openai.com/api-keys
    OPENAI_MODEL      optional — defaults to gpt-image-1. Also accepts
                      gpt-image-1-mini / gpt-image-1.5.
    OPENAI_QUALITY    optional — "low", "medium" (default), "high", or "auto".
                      Default is "medium" so users don't accidentally burn
                      credits on "high" for iteration rounds.

gpt-image-1 is synchronous and always returns base64 (the legacy
response_format=url flag is not supported for GPT image models). Supported
sizes: "auto", "1024x1024", "1536x1024" (landscape), "1024x1536" (portrait).
"""

from __future__ import annotations

import base64
import json
import os
import socket
import urllib.error
import urllib.request

DEFAULT_MODEL = "gpt-image-1"
DEFAULT_QUALITY = "medium"
_ALLOWED_QUALITIES = {"low", "medium", "high", "auto"}
ENDPOINT = "https://api.openai.com/v1/images/generations"
_SUPPORTED_SIZES = [(1024, 1024), (1536, 1024), (1024, 1536)]


def _error_detail(body: str, limit: int = 300) -> str:
    """Truncate an API error body for safe logging."""
    s = (body or "").replace("\n", " ").strip()
    return s[:limit] + ("…" if len(s) > limit else "")


def _api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return key


def _model() -> str:
    return os.environ.get("OPENAI_MODEL", "").strip() or DEFAULT_MODEL


def _quality() -> str:
    q = os.environ.get("OPENAI_QUALITY", "").strip().lower() or DEFAULT_QUALITY
    if q not in _ALLOWED_QUALITIES:
        raise RuntimeError(
            f"OPENAI_QUALITY={q!r} is invalid. Expected one of: "
            f"{', '.join(sorted(_ALLOWED_QUALITIES))}."
        )
    return q


def _closest_size(width: int, height: int) -> str:
    target = width / height
    best = min(_SUPPORTED_SIZES, key=lambda wh: abs(wh[0] / wh[1] - target))
    return f"{best[0]}x{best[1]}"


def generate(prompt: str, width: int, height: int) -> bytes:
    body = {
        "model": _model(),
        "prompt": prompt,
        "n": 1,
        "size": _closest_size(int(width), int(height)),
        "quality": _quality(),
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {_api_key()}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI image generation failed: HTTP {e.code} — {_error_detail(detail)}") from e
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        raise RuntimeError(f"OpenAI image generation failed: network error ({type(e).__name__})") from e

    items = payload.get("data", [])
    if not items or not items[0].get("b64_json"):
        raise RuntimeError("OpenAI response missing data[0].b64_json")
    return base64.b64decode(items[0]["b64_json"])
