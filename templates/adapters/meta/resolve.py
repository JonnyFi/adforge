#!/usr/bin/env python3
"""Meta adapter — resolve free-form targeting strings to Meta IDs, in place.

Reads a campaign plan, walks every adset.targeting.<field>, and for each
free-form string calls Meta's targeting search API to resolve it to
`{"id", "name", "audience_size"}`. Writes the resolved plan back.

Supported fields (all optional in the plan):
    interests       → type=adinterest
    work_positions  → type=adworkposition
    work_employers  → type=adworkemployer
    industries      → type=adTargetingCategory&class=industries
    behaviors       → type=adTargetingCategory&class=behaviors

Already-resolved entries (objects with an `id`) are skipped. The plan file is
the only state — re-runs are idempotent.

Modes:
    (default)       interactive: for each query, show top-3 candidates, prompt pick.
    --auto          auto-pick the top candidate when it's dominant (exact name
                    match or >5× the audience size of the runner-up). Unresolved
                    queries are listed and exit is non-zero.

Usage:
    python3 adapters/meta/resolve.py <campaign-plan.json>
    python3 adapters/meta/resolve.py --auto <campaign-plan.json>
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from deploy import API, derive_locale, load_brand, load_env, find_project_root
from _http import bearer_headers, redact_body


# plan-field → (search type, extra params). Used by resolve_query.
FIELD_MAP = {
    "interests":      ("adinterest",          {}),
    "work_positions": ("adworkposition",      {}),
    "work_employers": ("adworkemployer",      {}),
    "industries":     ("adTargetingCategory", {"class": "industries"}),
    "behaviors":      ("adTargetingCategory", {"class": "behaviors"}),
}

DOMINANCE_RATIO = 5  # top audience_size must be >= N× runner-up for --auto pick


def search(session, token, type_, q, locale=None, limit=8, extra=None):
    params = {"type": type_, "q": q, "limit": limit}
    if locale:
        params["locale"] = locale
    if extra:
        params.update(extra)
    r = session.get(f"{API}/search", params=params, headers=bearer_headers(token))
    if r.status_code >= 400:
        raise RuntimeError(f"search {type_} q={q!r} failed {r.status_code}: {redact_body(r.text)}")
    return r.json().get("data", [])


def option_active(session, token, type_, id_):
    """Check targetingoptionstatus. Returns True unless the option is explicitly
    NON-DELIVERABLE. We drop NON-DELIVERABLE silently and keep DEPRECATING since
    Meta still accepts them for now — this is internal hygiene, not user-facing.
    """
    try:
        r = session.get(
            f"{API}/search",
            params={
                "type": "targetingoptionstatus",
                "targeting_list": json.dumps([{"type": type_, "id": str(id_)}]),
            },
            headers=bearer_headers(token),
        )
        if r.status_code >= 400:
            return True  # fail open — don't drop on transient API error
        data = r.json().get("data", [])
        if not data:
            return True
        status = data[0].get("current_status", "NORMAL")
        return status != "NON_DELIVERABLE"
    except Exception:
        return True


def dominant(candidates):
    """Return the first candidate if it's clearly the best match.

    Dominance = (a) exact case-insensitive name match AND no equally-exact
    runner-up, or (b) audience_size >= 5× runner-up.
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    top, runner = candidates[0], candidates[1]
    top_size = int(top.get("audience_size") or 0)
    runner_size = int(runner.get("audience_size") or 1)
    if runner_size == 0:
        runner_size = 1
    if top_size and top_size / runner_size >= DOMINANCE_RATIO:
        return top
    return None


def format_candidate(c):
    name = c.get("name", "?")
    size = c.get("audience_size")
    path = " › ".join(c.get("path", [])) if c.get("path") else ""
    size_s = f"{size:,}" if isinstance(size, int) else "?"
    trail = f"  [{path}]" if path else ""
    return f"{name} · {size_s} people{trail}"


def resolve_query(session, token, type_, query, locale, extra, auto, unresolved_log):
    raw = search(session, token, type_, query, locale=locale, extra=extra)
    # silent hygiene — filter NON_DELIVERABLE
    candidates = [c for c in raw if option_active(session, token, type_, c.get("id"))]
    if not candidates:
        unresolved_log.append((type_, query, "no matches"))
        return None

    if auto:
        pick = dominant(candidates)
        if pick is None:
            unresolved_log.append((type_, query, f"ambiguous — top: {format_candidate(candidates[0])}"))
            return None
    else:
        print(f"\n  query: {query!r}  ({type_})")
        top = candidates[:3]
        for i, c in enumerate(top, 1):
            print(f"    {i}. {format_candidate(c)}")
        print(f"    s) skip")
        while True:
            choice = input("  pick [1-3/s]: ").strip().lower()
            if choice == "s":
                unresolved_log.append((type_, query, "user skipped"))
                return None
            if choice in {"1", "2", "3"} and int(choice) <= len(top):
                pick = top[int(choice) - 1]
                break
            print("    invalid — pick 1-3 or s")

    return {
        "id": str(pick["id"]),
        "name": pick.get("name", query),
        "audience_size": pick.get("audience_size"),
    }


def walk_targeting(plan, resolver):
    """Mutate plan in place — for each adset.targeting.<field> in FIELD_MAP,
    turn any free-form string entries into resolved objects. Leaves already-
    resolved objects untouched.
    """
    for campaign in plan.get("campaigns", []):
        for adset in campaign.get("adsets", []):
            t = adset.get("targeting", {})
            for field, (type_, extra) in FIELD_MAP.items():
                entries = t.get(field)
                if not entries:
                    continue
                resolved = []
                for entry in entries:
                    if isinstance(entry, dict) and entry.get("id"):
                        resolved.append(entry)
                        continue
                    if not isinstance(entry, str):
                        continue
                    picked = resolver(type_, entry, extra)
                    if picked:
                        resolved.append(picked)
                t[field] = resolved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", help="path to campaign plan JSON")
    ap.add_argument("--auto", action="store_true",
                    help="auto-pick dominant matches; exit non-zero if anything is ambiguous")
    args = ap.parse_args()

    plan_path = Path(args.plan)
    project_root = find_project_root(plan_path)
    env = {**os.environ, **load_env(project_root)}
    token = env.get("META_ACCESS_TOKEN", "")
    if not token:
        raise SystemExit("error: META_ACCESS_TOKEN not set (in .env or env)")

    brand = load_brand(project_root)
    locale_info = derive_locale(brand.get("domain", ""))
    # Meta's `locale` param only accepts a fixed set of `language_TERRITORY`
    # values (e.g. de_DE, en_US, fr_FR). de_AT / de_CH / nl_BE are rejected.
    # We map derived locales to the dominant-territory variant Meta supports —
    # this controls the language of returned names, NOT which country the ads
    # target (that's `geo_locations`, set independently from the TLD).
    LANG_TO_META_LOCALE = {
        "de": "de_DE", "fr": "fr_FR", "nl": "nl_NL", "it": "it_IT",
        "es": "es_ES", "pt": "pt_BR", "en": "en_US", "pl": "pl_PL",
        "sv": "sv_SE", "da": "da_DK", "fi": "fi_FI", "nb": "nb_NO",
    }
    search_locale = None
    if locale_info:
        search_locale = LANG_TO_META_LOCALE.get(locale_info["language"])

    plan = json.loads(plan_path.read_text())
    session = requests.Session()
    unresolved = []

    def resolver(type_, query, extra):
        return resolve_query(
            session, token, type_, query, search_locale, extra,
            auto=args.auto, unresolved_log=unresolved,
        )

    walk_targeting(plan, resolver)

    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
    print(f"\nwrote resolved plan -> {plan_path}")

    if unresolved:
        print(f"\n{len(unresolved)} unresolved:")
        for t, q, reason in unresolved:
            print(f"  - {t}  {q!r}  ({reason})")
        if args.auto:
            print("\nRe-run without --auto to pick interactively, or paste IDs manually:")
            print('  "interests": [{"id": "12345", "name": "..."}]')
            sys.exit(1)


if __name__ == "__main__":
    main()
