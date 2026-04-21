"""
Google Gemini image generation — "Nano Banana" (gemini-2.5-flash-image).

Docs: https://ai.google.dev/gemini-api/docs/image-generation
Verified: 2026-04-20

Env:
    GEMINI_API_KEY              required — https://aistudio.google.com/apikey
    GOOGLE_AI_STUDIO_API_KEY    accepted as alias
    GEMINI_MODEL                optional — defaults to gemini-2.5-flash-image

Gemini's image API is synchronous: POST generateContent with the prompt,
responseModalities=["TEXT","IMAGE"] and an imageConfig.aspectRatio derived from
the requested width/height. The response carries the PNG inline as base64 in
candidates[0].content.parts[*].inlineData.data.
"""

from __future__ import annotations

import base64
import json
import math
import os
import urllib.error
import urllib.request

DEFAULT_MODEL = "gemini-2.5-flash-image"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

# Aspect ratios Gemini's imageConfig accepts (from the public docs).
_SUPPORTED_ASPECTS = [
    (1, 1), (1, 4), (1, 8), (2, 3), (3, 2), (3, 4), (4, 1),
    (4, 3), (4, 5), (5, 4), (8, 1), (9, 16), (16, 9), (21, 9),
]


def _api_key() -> str:
    key = (
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_AI_STUDIO_API_KEY", "").strip()
    )
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set (GOOGLE_AI_STUDIO_API_KEY also accepted)"
        )
    return key


def _model() -> str:
    return os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL


def _closest_aspect(width: int, height: int) -> str:
    target = width / height
    best = min(_SUPPORTED_ASPECTS, key=lambda ab: abs(math.log(ab[0] / ab[1]) - math.log(target)))
    return f"{best[0]}:{best[1]}"


def generate(prompt: str, width: int, height: int) -> bytes:
    key = _api_key()
    model = _model()
    url = f"{ENDPOINT}/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        "imageConfig": {"aspectRatio": _closest_aspect(int(width), int(height))},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-goog-api-key", key)

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini generate failed: HTTP {e.code} — {detail}") from e

    for cand in payload.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])

    raise RuntimeError(f"Gemini response had no inlineData image: {payload!r}")
