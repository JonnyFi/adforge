---
name: image-provider-synth
description: Backend skill — write a new image-generation provider adapter under engines/static/image_providers/ when the user brings a provider adforge doesn't have built-in. Use when the user has an API key for a provider other than BFL, Google, OpenAI, Replicate, Stability, or fal.
---

# image-provider-synth

Generate a working `engines/static/image_providers/<name>.py` adapter for a provider adforge doesn't yet ship. The user tells you "I have a key for X" where X isn't one of the six built-ins — you write the adapter, the dispatcher picks it up automatically.

This skill exists because adforge promises provider-neutrality, but no unified HTTP standard covers image-generation APIs. Each provider has its own shape. Instead of pretending to support a long-tail provider out of the box, we write the adapter on demand, from the provider's own docs.

## When to invoke

- The user says they have an API key for a provider whose name doesn't match any file in `engines/static/image_providers/`.
- The user's existing stack uses a provider adforge doesn't ship (e.g. Mistral, Luma, Ideogram, Runway, Amazon Bedrock, Azure OpenAI, Together, Cloudflare Workers AI, a self-hosted Comfy/InvokeAI endpoint).
- An ops user wants to wire a corporate inference gateway that mimics one of the supported APIs.

If the provider is already in `engines/static/image_providers/` as a built-in (`bfl`, `google`, `openai`, `replicate`, `stability`, `fal`), do NOT synthesize — the user just needs to set the env var.

## Non-negotiable: sources of truth

Build the adapter **only** from:

- The provider's official developer documentation (`<provider>.com/docs`, `docs.<provider>.*`, `api-docs.<provider>.*`, …).
- The provider's official GitHub repos, SDKs, or OpenAPI specs.
- Their official changelog / model cards.

**Never** guess endpoint paths, header names, request shapes, or response fields from training-data recall. Never base an adapter on Stack Overflow, Medium articles, YouTube videos, or random blog posts. If the docs are ambiguous, send one live request with the user's throwaway key, observe the actual shape in the response, and cite what you observed.

At the top of every adapter you write, include the primary docs URL(s) and today's date as the verification date. If a future reader doubts the adapter, they can re-verify against the same source.

## Read the contract first

`engines/static/image_providers/CONTRACT.md` is the spec. Every adapter in that dir must satisfy it:

- One function: `generate(prompt: str, width: int, height: int) -> bytes`.
- Env vars: `<PROVIDER>_API_KEY` (or the provider's canonical variable if different — `REPLICATE_API_TOKEN`, `FAL_KEY`), plus optional `<PROVIDER>_MODEL`.
- Stdlib only (`urllib.request`, `json`, `base64`, `time`, `os`, `secrets`). Pillow is available. Nothing else unless the provider literally ships no REST surface.
- Raise `RuntimeError` with a human-readable message on any failure (missing key, bad response, moderation block, quota exhausted).
- Map the requested width/height to the closest aspect or size the provider supports. Don't error out on arbitrary sizes unless the provider literally refuses.

## Read a reference adapter before writing

Two shipped adapters cover the two common shapes. Read whichever matches before writing:

- **Sync request/response** — `engines/static/image_providers/openai.py`. Block until the API returns a base64 payload or a URL.
- **Queue + poll** — `engines/static/image_providers/bfl.py`. POST returns a job ID + polling URL; loop until status is terminal; download the final image.

Providers that return a URL instead of bytes: follow the `_download(url)` pattern from `bfl.py` or `fal.py`.

## Process

### 1. Gather the primary docs

Open the provider's docs page. Capture exactly, without paraphrasing:

1. The full REST URL for the "generate image" endpoint.
2. The authentication header format (`Authorization: Bearer $KEY`, `x-api-key`, `x-goog-api-key`, etc).
3. The content-type — JSON body, multipart/form-data, or form-urlencoded.
4. Every required request field.
5. The response shape — where the image lives (raw bytes, `b64_json`, `inlineData.data`, a URL inside `output`, `images[0].url`).
6. If asynchronous: how to poll (status values, polling URL shape) and where the image appears when done.
7. The provider's default / recommended model and whether width/height are specified as pixels, aspect ratio, or a named preset.

Paste the doc URL(s) and today's date into the top-of-file comment of the adapter you're about to write.

### 2. Pick a file name

`engines/static/image_providers/<name>.py`. Short, single-word, lowercase. Match the provider's canonical slug:

- Mistral → `mistral.py`
- Amazon Bedrock → `bedrock.py`
- Azure OpenAI → `azure.py`
- Cloudflare Workers AI → `cloudflare.py`
- Self-hosted Comfy endpoint → ask the user what to call it (e.g. `comfy.py`, `local.py`)

Don't collide with an existing file. `ls engines/static/image_providers/` before you write.

### 3. Decide the env vars

- `<PROVIDER>_API_KEY` is the default. If the provider's docs use a different canonical name (like `REPLICATE_API_TOKEN`), use theirs — users hate renaming standard env vars.
- `<PROVIDER>_MODEL` is optional; users override the default model this way. Always support it.
- Do not introduce any other env vars. No `<PROVIDER>_BASE_URL`, no `<PROVIDER>_REGION`, no `<PROVIDER>_ORG` unless the provider's API literally cannot function without it. Setup should not be a tutorial per provider.

### 4. Draft the adapter

Skeleton for a sync provider:

```python
"""
<Provider> image generation.

Docs: <official docs URL>
Verified: <today's date>

Env:
    <PROVIDER>_API_KEY   required — <where to get it>
    <PROVIDER>_MODEL     optional — defaults to <model>

<one-line description of the request/response style>
"""

from __future__ import annotations

import base64  # only if response is b64
import json
import os
import urllib.error
import urllib.request

DEFAULT_MODEL = "<sensible default>"
ENDPOINT = "<full URL>"


def _api_key() -> str:
    key = os.environ.get("<PROVIDER>_API_KEY", "").strip()
    if not key:
        raise RuntimeError("<PROVIDER>_API_KEY is not set")
    return key


def _model() -> str:
    return os.environ.get("<PROVIDER>_MODEL", "").strip() or DEFAULT_MODEL


def generate(prompt: str, width: int, height: int) -> bytes:
    body = {...}  # per docs
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {_api_key()}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"<Provider> generate failed: HTTP {e.code} — {detail}") from e
    # Extract image bytes per response shape
    ...
    return image_bytes
```

Skeleton for a queue provider: see `bfl.py` or `fal.py` — mirror the submit → poll → download shape.

### 5. Map width/height

Every provider accepts size differently:

- **Discrete sizes** (OpenAI: 1024x1024, 1536x1024, 1024x1536) — pick the closest by target aspect ratio.
- **Aspect strings** (Gemini, Replicate, Stability: `1:1`, `16:9`, …) — pick the closest by log-ratio. See `google.py::_closest_aspect` for the pattern.
- **Raw pixels** (BFL, fal) — pass width and height through as-is.
- **Named presets** (some providers: `square`, `landscape`) — map to the preset closest to the target aspect.

Don't error out on non-standard sizes. Just pick the closest supported value.

### 6. Test end-to-end before declaring done

1. Ask the user to drop their key into `.env`.
2. Run the adapter via the dispatcher:
   ```
   IMAGE_PROVIDER=<name> python3 engines/static/generate_hero.py /tmp/test.png 1024 1024 <<<"a simple test prompt"
   ```
3. Open the file. Check it's a valid PNG/JPEG and the content roughly matches the prompt.
4. Run `./test/run-tests.sh --skip-motion`. The dispatcher's shape-test suite catches wrong endpoint, missing auth, bad body shape.

If any of these fail, fix the adapter — don't ship broken. Re-verify against the docs, and if they're ambiguous, do a curl by hand to see the actual response shape before editing.

### 7. Optional: add a shape test

If the adapter is likely to be shared back to adforge upstream, write a mock-HTTP shape test mirroring Test 2g in `test/run-tests.sh`. Stub `urllib.request.urlopen`, assert endpoint + headers + body shape + response parsing. The existing tests are the template — copy the pattern for your provider.

## Rules

- **Docs first.** If you can't find the endpoint in official docs in 5 minutes, ask the user for the doc URL. Don't invent it.
- **No SDK dependencies.** The whole point of stdlib-only is that `npx adforge init` runs everywhere. If a provider's API is genuinely unreachable without an SDK, flag it to the user — don't silently add a dependency.
- **Don't modify other adapters** to "normalize" them with the new one. Each adapter is self-contained.
- **Don't touch the dispatcher** unless adding auto-detection for the new provider is warranted. Auto-detection in `generate_hero.py::DETECTION_ORDER` should only include providers adforge ships by default; user-synthesized adapters work via `IMAGE_PROVIDER=<name>`.
- **Cite and date.** Every adapter's top-of-file comment carries the docs URL and the verification date. Future-you will thank present-you when an endpoint changes.
