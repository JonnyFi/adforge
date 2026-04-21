"""
Replicate — unified gateway for image generation models.

Docs: https://replicate.com/docs/reference/http
Verified: 2026-04-20

Env:
    REPLICATE_API_TOKEN   required — https://replicate.com/account/api-tokens
    REPLICATE_MODEL       optional — defaults to google/nano-banana-2
                          (top trending model on Replicate as of 2026-04).

Replicate speaks a queue-like API: POST /v1/models/<owner>/<name>/predictions
returns a prediction with urls.get to poll. Passing `Prefer: wait=60` makes
the initial POST block until the prediction finishes (or times out) so we
mostly avoid polling for the default fast models.
"""

from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = "google/nano-banana-2"
ENDPOINT = "https://api.replicate.com/v1"
POLL_MAX_ATTEMPTS = 60
POLL_INTERVAL_SECONDS = 2

_SUPPORTED_ASPECTS = [
    (1, 1), (16, 9), (9, 16), (4, 3), (3, 4), (21, 9), (3, 2), (2, 3),
    (4, 5), (5, 4),
]


def _api_token() -> str:
    key = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not key:
        raise RuntimeError("REPLICATE_API_TOKEN is not set")
    return key


def _model() -> str:
    return os.environ.get("REPLICATE_MODEL", "").strip() or DEFAULT_MODEL


def _closest_aspect(width: int, height: int) -> str:
    target = width / height
    best = min(_SUPPORTED_ASPECTS, key=lambda ab: abs(math.log(ab[0] / ab[1]) - math.log(target)))
    return f"{best[0]}:{best[1]}"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_api_token()}",
        "Content-Type": "application/json",
    }


def _post(url: str, body: dict, wait: bool) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in _headers().items():
        req.add_header(k, v)
    if wait:
        req.add_header("Prefer", "wait=60")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Replicate predict failed: HTTP {e.code} — {detail}") from e


def _get(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {_api_token()}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Replicate poll failed: HTTP {e.code} — {detail}") from e


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Replicate output download failed: HTTP {e.code}") from e


def _extract_url(output) -> str | None:
    """Replicate outputs vary by model: a string, a list of strings, or an
    object with a 'url' field. Walk the common shapes."""
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output:
        return _extract_url(output[0])
    if isinstance(output, dict):
        for key in ("url", "image", "image_url"):
            if key in output:
                return _extract_url(output[key])
    return None


def generate(prompt: str, width: int, height: int) -> bytes:
    model = _model()
    url = f"{ENDPOINT}/models/{model}/predictions"
    body = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": _closest_aspect(int(width), int(height)),
        }
    }

    pred = _post(url, body, wait=True)
    status = pred.get("status", "")

    if status not in {"succeeded", "failed", "canceled"}:
        poll_url = pred.get("urls", {}).get("get")
        if not poll_url:
            raise RuntimeError(f"Replicate response missing urls.get: {pred!r}")
        for _ in range(POLL_MAX_ATTEMPTS):
            time.sleep(POLL_INTERVAL_SECONDS)
            pred = _get(poll_url)
            status = pred.get("status", "")
            if status in {"succeeded", "failed", "canceled"}:
                break
        else:
            raise RuntimeError(
                f"Replicate prediction {pred.get('id')!r} did not finish in "
                f"{POLL_MAX_ATTEMPTS * POLL_INTERVAL_SECONDS}s"
            )

    if status != "succeeded":
        raise RuntimeError(f"Replicate prediction ended in status {status}: {pred!r}")

    out_url = _extract_url(pred.get("output"))
    if not out_url:
        raise RuntimeError(f"Replicate succeeded but output missing a URL: {pred!r}")
    return _download(out_url)
