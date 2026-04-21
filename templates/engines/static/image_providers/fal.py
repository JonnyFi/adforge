"""
fal.ai — queue API for image generation.

Docs: https://docs.fal.ai/model-apis/model-endpoints/queue
Verified: 2026-04-20

Env:
    FAL_KEY       required — https://fal.ai/dashboard/keys
    FAL_MODEL     optional — defaults to fal-ai/flux/schnell (fast + cheap).

fal is queue-based: POST returns request_id + status_url + response_url;
poll status_url until status == "COMPLETED", then GET response_url for the
payload and download the first image URL.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = "fal-ai/flux/schnell"
ENDPOINT = "https://queue.fal.run"
POLL_MAX_ATTEMPTS = 60
POLL_INTERVAL_SECONDS = 2


def _api_key() -> str:
    key = os.environ.get("FAL_KEY", "").strip()
    if not key:
        raise RuntimeError("FAL_KEY is not set")
    return key


def _model() -> str:
    return os.environ.get("FAL_MODEL", "").strip() or DEFAULT_MODEL


def _headers() -> dict:
    return {"Authorization": f"Key {_api_key()}"}


def _post(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in _headers().items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"fal submit failed: HTTP {e.code} — {detail}") from e


def _get(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    for k, v in _headers().items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"fal poll failed: HTTP {e.code} — {detail}") from e


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"fal image download failed: HTTP {e.code}") from e


def generate(prompt: str, width: int, height: int) -> bytes:
    submit_url = f"{ENDPOINT}/{_model()}"
    body = {
        "prompt": prompt,
        "image_size": {"width": int(width), "height": int(height)},
    }
    submit = _post(submit_url, body)
    status_url = submit.get("status_url")
    response_url = submit.get("response_url")
    if not status_url or not response_url:
        raise RuntimeError(f"fal submit response missing status_url/response_url: {submit!r}")

    for _ in range(POLL_MAX_ATTEMPTS):
        time.sleep(POLL_INTERVAL_SECONDS)
        status = _get(status_url)
        state = status.get("status", "")
        if state == "COMPLETED":
            break
        if state not in {"IN_QUEUE", "IN_PROGRESS"}:
            raise RuntimeError(f"fal unexpected status {state!r}: {status!r}")
    else:
        raise RuntimeError(
            f"fal request {submit.get('request_id')!r} did not complete in "
            f"{POLL_MAX_ATTEMPTS * POLL_INTERVAL_SECONDS}s"
        )

    result = _get(response_url)
    images = result.get("images") or []
    if not images or not images[0].get("url"):
        raise RuntimeError(f"fal completed but response has no images[0].url: {result!r}")
    return _download(images[0]["url"])
