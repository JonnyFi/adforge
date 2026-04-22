"""Shared HTTP helpers for Meta adapter modules.

Two jobs:
    1. Put the access token in an `Authorization: Bearer ...` header instead of
       the URL query string. Query-string tokens land in corp-proxy access logs,
       test cassettes, and `--debug` output — Graph API v22.0 accepts Bearer.
    2. Truncate + sanitize error response bodies before they hit stderr. Meta's
       error payloads can echo back submitted fields, and callers tend to
       forward `r.text` verbatim into logs.
"""

from __future__ import annotations

import re


def bearer_headers(token: str) -> dict:
    """Return a headers dict carrying the access token as a Bearer token.

    Callers pass this to `requests.get/post(..., headers=bearer_headers(token))`
    and drop `access_token` from `params` / `data`.
    """
    return {"Authorization": f"Bearer {token}"}


_SENSITIVE_KEYS = re.compile(
    r'("(?:access_token|password|client_secret|appsecret_proof)"\s*:\s*")[^"]*(")',
    re.IGNORECASE,
)


def redact_body(text: str, limit: int = 300) -> str:
    """Truncate an API error body for safe logging.

    Meta's error responses can echo back submitted fields (including the
    access_token when legacy code paths leave it in the request). We strip
    those first, then truncate so one long payload can't flood the terminal.
    """
    if not text:
        return ""
    s = _SENSITIVE_KEYS.sub(r"\1<redacted>\2", text)
    s = s.replace("\n", " ").strip()
    return s[:limit] + ("…" if len(s) > limit else "")
