# Image provider contract

Every module in this directory is an image-generation provider. The dispatcher (`../generate_hero.py`) loads them by name and calls a single function. Add a new provider by dropping a new `.py` file here that satisfies the contract below.

## The function

```python
def generate(prompt: str, width: int, height: int) -> bytes:
    ...
```

- Returns the raw PNG (or JPEG) bytes. The dispatcher writes them to the output path.
- Takes exactly three arguments. No keyword-only args, no config dicts. Keep the surface boring.
- If the provider's API doesn't support arbitrary widths/heights, pick the closest supported aspect / resolution and return that. Don't error out on non-standard sizes unless the provider literally refuses.
- Raise `RuntimeError` with a human-readable message on any failure (missing key, bad response, moderation block, quota exhausted). The dispatcher catches and surfaces these.

## Environment

- Read the API key from an env var named `<PROVIDER>_API_KEY` (or the provider's canonical env var if different — e.g. `REPLICATE_API_TOKEN` is standard). Document which env var you use at the top of the module.
- Support a `<PROVIDER>_MODEL` env var that overrides the module's default model.
- No other env vars. Users shouldn't need a tutorial per provider.

## Defaults

- Pick a sensible default model — the one the provider themselves recommend, not the cheapest or the flagship. Users can override via env.
- Prefer native PNG/JPEG output. If the API returns base64 or URL, decode/download inside the module and return bytes.

## Sources of truth — non-negotiable

When writing a new provider module, build **only** from:

- The provider's official developer documentation (e.g. `platform.openai.com/docs`, `ai.google.dev/gemini-api/docs`, `replicate.com/docs`).
- The provider's official GitHub repos, SDKs, or OpenAPI specs.
- Their official changelog / model cards.

**Never** guess endpoint paths, header names, request shapes, or response fields from training-data recall. Never base an adapter on Stack Overflow, Medium articles, or random blog posts. If the docs are ambiguous, send one live request with a throwaway key, observe the shape, and cite what you observed.

At the top of each module, comment the primary docs URL(s) and the date you verified them against:

```python
# OpenAI Images API — https://platform.openai.com/docs/api-reference/images/create
# Verified: 2026-04-21
```

## Two reference implementations

The built-in modules are the canonical examples. Read them before writing a new one:

- **`bfl.py`** — async submit-then-poll pattern. BFL returns a job ID and a polling URL; the adapter loops until the job is `Ready`, then downloads the resulting image from the returned URL. Use this shape for any provider that queues work rather than blocking.
- **`openai.py`** — sync request/response pattern. Returns base64 inline in the response body. Use this shape for providers that block until the image is ready.

Providers that return a URL instead of bytes: follow `bfl.py`'s `urllib.request.urlopen` pattern for the download step.

## Keep it stdlib

All built-in adapters use only the Python standard library (`urllib.request`, `json`, `base64`, `os`, `time`). Pillow is available. Nothing else. If your adapter *really* needs a vendor SDK, justify it in a comment — added deps land in `requirements.txt`.

## Testing your new provider

1. `IMAGE_PROVIDER=<name> python3 engines/static/generate_hero.py /tmp/test.png 1024 1024 <<<"a simple test prompt"` — should produce a valid PNG.
2. Run `./test/run-tests.sh --skip-motion` — the dispatcher's shape-test suite catches common mistakes (wrong endpoint, missing auth header).
3. Open the resulting image. If it renders, your adapter works end-to-end.
