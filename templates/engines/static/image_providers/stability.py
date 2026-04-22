"""
Stability AI — Stable Image Core (and siblings).

Docs: https://platform.stability.ai/docs/api-reference
Verified: 2026-04-20

Env:
    STABILITY_API_KEY   required — https://platform.stability.ai/account/keys
    STABILITY_MODEL     optional — one of "core" (default), "ultra", "sd3".
                        Maps to /v2beta/stable-image/generate/<model>.

Stability expects multipart/form-data, even though there are no files in the
request. Accept: image/* makes it stream raw PNG/JPEG bytes straight back, so
no b64 decoding is needed.
"""

from __future__ import annotations

import math
import os
import secrets
import socket
import urllib.error
import urllib.request


def _error_detail(body: str, limit: int = 300) -> str:
    """Truncate an API error body for safe logging."""
    s = (body or "").replace("\n", " ").strip()
    return s[:limit] + ("…" if len(s) > limit else "")

DEFAULT_MODEL = "core"  # maps to .../generate/core
ENDPOINT = "https://api.stability.ai/v2beta/stable-image/generate"

_SUPPORTED_ASPECTS = [
    (1, 1), (16, 9), (9, 16), (21, 9), (9, 21), (3, 2), (2, 3), (4, 5), (5, 4),
]


def _api_key() -> str:
    key = os.environ.get("STABILITY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("STABILITY_API_KEY is not set")
    return key


def _model() -> str:
    return os.environ.get("STABILITY_MODEL", "").strip() or DEFAULT_MODEL


def _closest_aspect(width: int, height: int) -> str:
    target = width / height
    best = min(_SUPPORTED_ASPECTS, key=lambda ab: abs(math.log(ab[0] / ab[1]) - math.log(target)))
    return f"{best[0]}:{best[1]}"


def _build_multipart(fields: dict) -> tuple[bytes, str]:
    """Minimal multipart/form-data encoder (all fields are simple strings)."""
    boundary = f"----adforge{secrets.token_hex(16)}"
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        lines.append(b"")
        lines.append(str(value).encode("utf-8"))
    lines.append(f"--{boundary}--".encode())
    lines.append(b"")
    body = b"\r\n".join(lines)
    return body, boundary


def generate(prompt: str, width: int, height: int) -> bytes:
    url = f"{ENDPOINT}/{_model()}"
    fields = {
        "prompt": prompt,
        "aspect_ratio": _closest_aspect(int(width), int(height)),
        "output_format": "png",
    }
    body, boundary = _build_multipart(fields)
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {_api_key()}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Accept", "image/*")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Stability generate failed: HTTP {e.code} — {_error_detail(detail)}") from e
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        raise RuntimeError(f"Stability generate failed: network error ({type(e).__name__})") from e
