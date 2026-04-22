"""
Black Forest Labs (FLUX) image provider.

Docs: https://docs.bfl.ai/api-reference (async submit-then-poll pattern)
Verified: 2026-04-21

Env:
    BFL_API_KEY   required — https://dashboard.bfl.ai/keys
    BFL_MODEL     optional — defaults to flux-2-pro. Other options:
                  flux-2-max, flux-2-flex, flux-pro-1.1, flux-schnell, …

The BFL API is asynchronous: POST /v1/<model> returns {id, polling_url},
then GET polling_url loops until status is "Ready" and result.sample holds
the image URL.
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = "flux-2-pro"  # CONTRACT.md:25 — "not the cheapest or the flagship"
ENDPOINT = "https://api.bfl.ai/v1"
POLL_MAX_ATTEMPTS = 60
POLL_INTERVAL_SECONDS = 2

# BFL requires width/height in [256, 1440] and divisible by 32.
_DIM_MIN = 256
_DIM_MAX = 1440
_DIM_STEP = 32


def _eprint(msg: str) -> None:
    import sys
    print(msg, file=sys.stderr)


def _api_key() -> str:
    key = os.environ.get("BFL_API_KEY", "").strip()
    if not key:
        raise RuntimeError("BFL_API_KEY is not set")
    return key


def _model() -> str:
    return os.environ.get("BFL_MODEL", "").strip() or DEFAULT_MODEL


def _error_detail(body: str, limit: int = 300) -> str:
    """Truncate an API error body for safe logging. Prompt echoes and response
    payloads don't belong in stderr; a short hint is enough to diagnose."""
    s = (body or "").replace("\n", " ").strip()
    return s[:limit] + ("…" if len(s) > limit else "")


def _snap_dims(width: int, height: int) -> tuple[int, int]:
    """Clamp (w, h) into BFL's valid range [_DIM_MIN, _DIM_MAX] preserving the
    requested aspect ratio, then round each dim to the nearest _DIM_STEP
    multiple. Clamping each dim independently (the previous behavior) silently
    destroyed aspect — e.g. 1728×2160 (4:5) became 1440×1440 (1:1) because
    both dims hit the cap. Now we scale proportionally first so a 4:5 request
    comes back ~4:5."""
    w_req = max(1, int(width))
    h_req = max(1, int(height))

    # 1) scale down proportionally if either dim exceeds the cap
    scale = min(1.0, _DIM_MAX / w_req, _DIM_MAX / h_req)
    # 2) scale up proportionally if either dim is below the floor
    scale = max(scale, _DIM_MIN / w_req, _DIM_MIN / h_req)

    w = w_req * scale
    h = h_req * scale

    # 3) round to 32-multiple and re-clamp (rounding can push past the edge)
    def _round_clamp(v: float) -> int:
        v = round(v / _DIM_STEP) * _DIM_STEP
        return int(max(_DIM_MIN, min(_DIM_MAX, v)))

    w_out, h_out = _round_clamp(w), _round_clamp(h)

    if (w_out, h_out) != (w_req, h_req):
        _eprint(
            f"[bfl] snapped requested {w_req}x{h_req} -> {w_out}x{h_out} "
            f"(BFL accepts {_DIM_MIN}–{_DIM_MAX}, multiples of {_DIM_STEP})"
        )
    return w_out, h_out


def _post_json(url: str, body: dict, headers: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"BFL submit failed: HTTP {e.code} — {_error_detail(detail)}") from e
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        raise RuntimeError(f"BFL submit failed: network error ({type(e).__name__})") from e


def _get_json(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"BFL poll failed: HTTP {e.code} — {_error_detail(detail)}") from e
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        raise RuntimeError(f"BFL poll failed: network error ({type(e).__name__})") from e


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"BFL image download failed: HTTP {e.code}") from e
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        raise RuntimeError(f"BFL image download failed: network error ({type(e).__name__})") from e


def generate(prompt: str, width: int, height: int) -> bytes:
    model = _model()
    headers = {"x-key": _api_key()}
    w, h = _snap_dims(width, height)
    body = {"prompt": prompt, "width": w, "height": h}

    submit = _post_json(f"{ENDPOINT}/{model}", body, headers)
    job_id = submit.get("id")
    polling_url = submit.get("polling_url")
    if not job_id or not polling_url:
        raise RuntimeError("BFL submit response missing id or polling_url")

    for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
        time.sleep(POLL_INTERVAL_SECONDS)
        poll = _get_json(polling_url, headers)
        status = poll.get("status", "")
        if status == "Ready":
            sample_url = poll.get("result", {}).get("sample")
            if not sample_url:
                raise RuntimeError(f"BFL job {job_id} Ready but result.sample missing")
            return _download(sample_url)
        if status in {"Error", "Failed", "Request Moderated", "Content Moderated"}:
            raise RuntimeError(f"BFL job {job_id} failed: {status}")

    raise RuntimeError(
        f"BFL job {job_id} did not reach Ready after "
        f"{POLL_MAX_ATTEMPTS * POLL_INTERVAL_SECONDS}s"
    )
