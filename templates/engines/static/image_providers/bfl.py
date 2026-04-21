"""
Black Forest Labs (FLUX) image provider.

Docs: https://docs.bfl.ai/api-reference (async submit-then-poll pattern)
Verified: 2026-04-21

Env:
    BFL_API_KEY   required — https://dashboard.bfl.ai/keys
    BFL_MODEL     optional — defaults to flux-2-max. Other options:
                  flux-2-pro, flux-2-flex, flux-pro-1.1, flux-schnell, …

The BFL API is asynchronous: POST /v1/<model> returns {id, polling_url},
then GET polling_url loops until status is "Ready" and result.sample holds
the image URL.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = "flux-2-max"
ENDPOINT = "https://api.bfl.ai/v1"
POLL_MAX_ATTEMPTS = 60
POLL_INTERVAL_SECONDS = 2


def _api_key() -> str:
    key = os.environ.get("BFL_API_KEY", "").strip()
    if not key:
        raise RuntimeError("BFL_API_KEY is not set")
    return key


def _model() -> str:
    return os.environ.get("BFL_MODEL", "").strip() or DEFAULT_MODEL


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
        raise RuntimeError(f"BFL submit failed: HTTP {e.code} — {detail}") from e


def _get_json(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"BFL poll failed: HTTP {e.code} — {detail}") from e


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"BFL image download failed: HTTP {e.code}") from e


def generate(prompt: str, width: int, height: int) -> bytes:
    model = _model()
    headers = {"x-key": _api_key()}
    body = {"prompt": prompt, "width": int(width), "height": int(height)}

    submit = _post_json(f"{ENDPOINT}/{model}", body, headers)
    job_id = submit.get("id")
    polling_url = submit.get("polling_url")
    if not job_id or not polling_url:
        raise RuntimeError(f"BFL submit response missing id/polling_url: {submit!r}")

    for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
        time.sleep(POLL_INTERVAL_SECONDS)
        poll = _get_json(polling_url, headers)
        status = poll.get("status", "")
        if status == "Ready":
            sample_url = poll.get("result", {}).get("sample")
            if not sample_url:
                raise RuntimeError(f"BFL Ready status missing result.sample: {poll!r}")
            return _download(sample_url)
        if status in {"Error", "Failed", "Request Moderated", "Content Moderated"}:
            raise RuntimeError(f"BFL job failed ({status}): {poll!r}")

    raise RuntimeError(
        f"BFL job {job_id} did not reach Ready after "
        f"{POLL_MAX_ATTEMPTS * POLL_INTERVAL_SECONDS}s"
    )
