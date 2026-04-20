#!/usr/bin/env python3
"""Meta adapter — deploy a campaign plan (JSON) via Graph API.

Idempotent: reads state file, skips already-created items, resumes on failure.
Everything PAUSED by default — nothing goes live without explicit flip.

Usage:
    python3 adapters/meta/deploy.py <campaign-plan.json>
    python3 adapters/meta/deploy.py --dry-run <campaign-plan.json>

Env (in .env or exported):
    META_ACCESS_TOKEN
    META_AD_ACCOUNT_ID   (e.g. act_123456789)
    META_PAGE_ID
    META_PIXEL_ID        (optional — for pixel-based optimization)
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import requests

API = "https://graph.facebook.com/v22.0"


def load_env(project_root):
    env_file = project_root / ".env"
    if not env_file.exists():
        return {}
    env = {}
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def find_project_root(start):
    p = Path(start).resolve()
    for parent in [p.parent, *p.parents]:
        if (parent / "adforge.config.json").exists():
            return parent
    raise SystemExit("no adforge.config.json found")


# TLD → {country, language}. Unambiguous TLDs only — ambiguous ones (.com, .ch, …)
# return None from derive_locale and force the caller to specify.
TLD_LOCALE = {
    "at": {"country": "AT", "language": "de"},
    "de": {"country": "DE", "language": "de"},
    "fr": {"country": "FR", "language": "fr"},
    "es": {"country": "ES", "language": "es"},
    "it": {"country": "IT", "language": "it"},
    "nl": {"country": "NL", "language": "nl"},
    "pl": {"country": "PL", "language": "pl"},
    "pt": {"country": "PT", "language": "pt"},
    "se": {"country": "SE", "language": "sv"},
    "no": {"country": "NO", "language": "no"},
    "dk": {"country": "DK", "language": "da"},
    "fi": {"country": "FI", "language": "fi"},
    "ie": {"country": "IE", "language": "en"},
    "us": {"country": "US", "language": "en"},
    "co.uk": {"country": "GB", "language": "en"},
    "uk": {"country": "GB", "language": "en"},
}


def derive_locale(domain):
    """Return {"country": "AT", "language": "de"} for unambiguous TLDs, else None.

    Accepts bare domains, URLs, or www-prefixed strings. Strips path. Recognises
    .co.uk as a two-label TLD. Returns None for generic TLDs (.com, .io, .co, …)
    and multi-lingual country TLDs (.ch, .be) so callers must specify explicitly.
    """
    if not domain:
        return None
    d = domain.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if d.startswith(prefix):
            d = d[len(prefix):]
    d = d.split("/")[0].split("?")[0]
    if d.endswith(".co.uk"):
        return TLD_LOCALE["co.uk"]
    if "." not in d:
        return None
    tld = d.rsplit(".", 1)[-1]
    return TLD_LOCALE.get(tld)


def load_brand(project_root):
    path = project_root / "brand.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def derive_placements(ads):
    """Return Meta placement fields based on asset types/formats in an adset.

    Rules (tuned for brand-feeling ads, not spray-and-pray):
      - static 4x5   → Feed (FB + IG)
      - static 9x16  → Stories only (no Reels — static in Reels looks cheap)
      - motion 4x5   → Feed
      - motion 9x16  → Reels + Stories
    Audience Network and Messenger are excluded by default (low-quality placements
    for most B2B/mid-consideration funnels). Callers can override by setting
    `publisher_platforms` / `facebook_positions` / `instagram_positions` on the
    adset's `targeting` directly — in that case `derive_placements` is skipped.
    """
    fb_positions = set()
    ig_positions = set()
    for ad in ads:
        fmt = ad.get("format", "4x5")
        is_video = ad.get("creative_type") == "video"
        if fmt == "4x5":
            fb_positions.add("feed")
            ig_positions.add("stream")
        elif fmt == "9x16":
            fb_positions.add("story")
            ig_positions.add("story")
            if is_video:
                fb_positions.add("facebook_reels")
                ig_positions.add("reels")
    out = {"publisher_platforms": ["facebook", "instagram"]}
    if fb_positions:
        out["facebook_positions"] = sorted(fb_positions)
    if ig_positions:
        out["instagram_positions"] = sorted(ig_positions)
    return out


# Fields that go into Meta's flexible_spec block. Plan carries them at the top
# level of `targeting` (after resolve.py turns strings into {id, name} objects);
# deploy collapses them into one AND-block inside flexible_spec.
FLEXIBLE_FIELDS = ("interests", "work_positions", "work_employers", "industries", "behaviors")


def build_flexible_spec(targeting, adset_name):
    """Collapse resolved targeting fields into a single flexible_spec AND-block.

    Raises if any entry is still a raw string (means resolve.py wasn't run).
    Leaves targeting untouched if none of the flexible fields are present.
    """
    block = {}
    for field in FLEXIBLE_FIELDS:
        entries = targeting.pop(field, None)
        if not entries:
            continue
        clean = []
        for e in entries:
            if isinstance(e, str):
                raise SystemExit(
                    f"error: adset '{adset_name}' has raw string {e!r} in targeting.{field} — "
                    f"run `python3 adapters/meta/resolve.py <plan>` first"
                )
            if isinstance(e, dict) and e.get("id"):
                clean.append({"id": str(e["id"]), "name": e.get("name", "")})
        if clean:
            block[field] = clean
    if not block:
        return
    existing = targeting.get("flexible_spec", [])
    targeting["flexible_spec"] = existing + [block]


def apply_advantage_audience(targeting):
    """Translate plan-level `advantage_audience: bool` into Meta's nested
    `targeting_automation.advantage_audience` (0/1) field.
    """
    if "advantage_audience" not in targeting:
        return
    flag = 1 if targeting.pop("advantage_audience") else 0
    ta = dict(targeting.get("targeting_automation", {}))
    ta["advantage_audience"] = flag
    targeting["targeting_automation"] = ta


# plan-level audience type → Meta customaudiences `subtype`. See
# https://developers.facebook.com/docs/marketing-api/audiences/reference/custom-audience-subtypes
AUDIENCE_SUBTYPES = {
    "custom_list": "CUSTOM",      # hashed customer file
    "pixel":       "WEBSITE",     # pixel-based retargeting
    "engagement":  "ENGAGEMENT",  # page/post/IG/video engagers
    "lookalike":   "LOOKALIKE",
}


def _hash_row(value):
    """Meta matching spec — SHA-256 of trimmed, lowercase UTF-8."""
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def upload_customer_file(meta, audience_id, csv_path):
    """Upload hashed user records to a CUSTOM audience in 10k-row batches.

    CSV header row defines the schema Meta expects (email, phone, first_name,
    last_name, city, state, zip, country, …). Values are hashed client-side;
    no raw PII leaves the machine.
    """
    import csv
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"customer file {csv_path} has no header row")
        schema = [k.lower() for k in reader.fieldnames]
        rows = [
            [_hash_row(row[col]) if row.get(col) else "" for col in reader.fieldnames]
            for row in reader
        ]
    if not rows:
        print(f"  [skip upload] {csv_path}: no rows")
        return
    BATCH = 10000
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        meta.post(f"{audience_id}/users", {
            "payload": json.dumps({"schema": schema, "data": batch}),
        })
        print(f"  [upload] {audience_id}: rows {i + 1}-{i + len(batch)}")


def ensure_audience(meta, state, aud, project_root, default_pixel_id):
    """Create a custom/lookalike audience if not in state. Returns the Meta ID.

    Mutates `state["audiences"]` on creation. Idempotent via the name key —
    rename an audience in the plan and you get a new audience on next deploy.
    """
    name = aud["name"]
    if name in state["audiences"]:
        aid = state["audiences"][name]
        print(f"[skip] audience '{name}' ({aid})")
        return aid

    kind = aud.get("type")
    subtype = AUDIENCE_SUBTYPES.get(kind)
    if not subtype:
        raise SystemExit(
            f"audience '{name}': unknown type {kind!r} "
            f"(expected one of {sorted(AUDIENCE_SUBTYPES)})"
        )

    data = {
        "name": name,
        "subtype": subtype,
        "description": aud.get("description", f"adforge: {name}"),
    }
    csv_path = None

    if kind == "custom_list":
        data["customer_file_source"] = aud.get(
            "customer_file_source", "USER_PROVIDED_ONLY"
        )
        src = aud.get("source_csv")
        if src:
            csv_path = Path(src)
            if not csv_path.is_absolute():
                csv_path = project_root / csv_path
            if not csv_path.exists():
                raise SystemExit(f"audience '{name}': source_csv not found at {csv_path}")

    elif kind == "pixel":
        pid = aud.get("pixel_id") or default_pixel_id
        if not pid:
            if meta.dry_run:
                pid = "<pixel_id>"
            else:
                raise SystemExit(
                    f"audience '{name}': pixel-based audience needs pixel_id "
                    f"(in the audience entry or via META_PIXEL_ID)"
                )
        retention = int(aud.get("retention_days", 180))
        rule = aud.get("rule") or {
            "inclusions": {
                "operator": "or",
                "rules": [{
                    "event_sources": [{"id": str(pid), "type": "pixel"}],
                    "retention_seconds": retention * 86400,
                    "filter": {"operator": "and", "filters": [
                        {"field": "event", "operator": "eq", "value": "PageView"},
                    ]},
                }],
            },
        }
        data["rule"] = json.dumps(rule)
        data["pixel_id"] = str(pid)
        data["retention_days"] = retention

    elif kind == "engagement":
        object_id = aud.get("object_id")
        object_type = aud.get("object_type", "page")
        if not object_id:
            raise SystemExit(
                f"audience '{name}': engagement audience needs object_id "
                f"(page/IG/post/video ID) and object_type"
            )
        retention = int(aud.get("retention_days", 365))
        rule = aud.get("rule") or {
            "inclusions": {
                "operator": "or",
                "rules": [{
                    "event_sources": [{"id": str(object_id), "type": object_type}],
                    "retention_seconds": retention * 86400,
                }],
            },
        }
        data["rule"] = json.dumps(rule)
        data["retention_days"] = retention

    elif kind == "lookalike":
        seed_ref = aud.get("seed")
        seed_id = None
        if isinstance(seed_ref, dict):
            seed_id = seed_ref.get("id")
        elif isinstance(seed_ref, str):
            seed_id = state["audiences"].get(seed_ref)
            if not seed_id:
                raise SystemExit(
                    f"audience '{name}': lookalike seed '{seed_ref}' not created yet — "
                    f"list it earlier in plan.audiences, or reference by id: "
                    f'{{"seed": {{"id": "12345"}}}}'
                )
        if not seed_id:
            raise SystemExit(
                f"audience '{name}': lookalike needs a seed "
                f"(name of another audience in the plan, or {{\"id\": \"...\"}})"
            )
        country = aud.get("country")
        if not country:
            raise SystemExit(f"audience '{name}': lookalike needs country (ISO-2, e.g. 'AT')")
        ratio = float(aud.get("ratio", 0.01))
        data["origin_audience_id"] = str(seed_id)
        data["lookalike_spec"] = json.dumps({
            "ratio": ratio,
            "country": country,
            "type": aud.get("similarity", "similarity"),
        })

    res = meta.post(f"{meta.ad_account}/customaudiences", data)
    aid = res["id"]
    state["audiences"][name] = aid
    print(f"[create] audience '{name}' ({aid})")

    if csv_path:
        if meta.dry_run:
            print(f"  [dry-run] would upload hashed rows from {csv_path}")
        else:
            upload_customer_file(meta, aid, str(csv_path))

    return aid


def ensure_audiences(plan, state, meta, project_root, pixel_id):
    for aud in plan.get("audiences", []):
        ensure_audience(meta, state, aud, project_root, pixel_id)
        state_save_side_effect(state, project_root, dry_run=meta.dry_run)


def resolve_audience_refs(targeting, adset_name, state):
    """Turn targeting.custom_audiences / excluded_custom_audiences string refs
    into [{id, name}] objects. Already-resolved {id: …} entries pass through.
    """
    for field in ("custom_audiences", "excluded_custom_audiences"):
        refs = targeting.get(field)
        if not refs:
            continue
        resolved = []
        for ref in refs:
            if isinstance(ref, dict) and ref.get("id"):
                resolved.append({"id": str(ref["id"]), "name": ref.get("name", "")})
                continue
            if isinstance(ref, str):
                aid = state["audiences"].get(ref)
                if not aid:
                    raise SystemExit(
                        f"adset '{adset_name}': targeting.{field} references '{ref}' — "
                        f"define it in plan.audiences or paste {{\"id\": \"...\"}} directly"
                    )
                resolved.append({"id": str(aid), "name": ref})
                continue
            raise SystemExit(
                f"adset '{adset_name}': targeting.{field} has invalid entry {ref!r}"
            )
        targeting[field] = resolved


def state_load(path):
    if path.exists():
        data = json.loads(path.read_text())
        # backfill keys added in later versions
        data.setdefault("audiences", {})
        return data
    return {
        "images": {}, "videos": {}, "campaigns": {}, "adsets": {},
        "creatives": {}, "ads": {}, "audiences": {},
    }


def state_save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False))


class Meta:
    def __init__(self, token, ad_account, dry_run=False):
        self.token = token
        self.ad_account = ad_account
        self.dry_run = dry_run
        self.s = requests.Session()

    def post(self, path, data=None, files=None):
        if self.dry_run:
            print(f"  [dry-run] POST {path} {json.dumps(data, ensure_ascii=False)[:120]}")
            return {"id": f"dry_{hashlib.md5(path.encode()).hexdigest()[:8]}"}
        data = dict(data or {})
        data["access_token"] = self.token
        url = f"{API}/{path.lstrip('/')}"
        r = self.s.post(url, data=data, files=files)
        if r.status_code >= 400:
            raise RuntimeError(f"POST {path} failed {r.status_code}: {r.text}")
        return r.json()

    def get(self, path, params=None):
        params = dict(params or {})
        params["access_token"] = self.token
        url = f"{API}/{path.lstrip('/')}"
        r = self.s.get(url, params=params)
        if r.status_code >= 400:
            raise RuntimeError(f"GET {path} failed {r.status_code}: {r.text}")
        return r.json()

    # --- upload helpers ---
    def upload_image(self, image_path):
        if self.dry_run:
            print(f"  [dry-run] upload image {image_path}")
            return f"dry_img_{hashlib.md5(str(image_path).encode()).hexdigest()[:8]}"
        with open(image_path, "rb") as f:
            res = self.post(f"{self.ad_account}/adimages", files={"file": f})
        # response format: {"images": {"basename": {"hash": "...", ...}}}
        imgs = res.get("images", {})
        if not imgs:
            raise RuntimeError(f"image upload failed: {res}")
        _, info = next(iter(imgs.items()))
        return info["hash"]

    def upload_video(self, video_path):
        if self.dry_run:
            print(f"  [dry-run] upload video {video_path}")
            return f"dry_vid_{hashlib.md5(str(video_path).encode()).hexdigest()[:8]}"
        with open(video_path, "rb") as f:
            res = self.post(f"{self.ad_account}/advideos", data={"name": Path(video_path).name}, files={"source": f})
        return res["id"]


def deploy(plan, state, meta, project_root, page_id, pixel_id):
    """Walk the plan and create everything that doesn't yet exist in state."""
    brand = load_brand(project_root)
    brand_locale = derive_locale(brand.get("domain", ""))
    ensure_audiences(plan, state, meta, project_root, pixel_id)
    for campaign in plan.get("campaigns", []):
        cname = campaign["name"]
        if cname in state["campaigns"]:
            cid = state["campaigns"][cname]
            print(f"[skip] campaign '{cname}' ({cid})")
        else:
            print(f"[create] campaign '{cname}'")
            res = meta.post(f"{meta.ad_account}/campaigns", {
                "name": cname,
                "objective": campaign.get("objective", "OUTCOME_TRAFFIC"),
                "status": campaign.get("status", "PAUSED"),
                "special_ad_categories": json.dumps(campaign.get("special_ad_categories", [])),
                "buying_type": "AUCTION",
            })
            cid = res["id"]
            state["campaigns"][cname] = cid
            state_save_side_effect(state, project_root, dry_run=meta.dry_run)

        for adset in campaign.get("adsets", []):
            aname = adset["name"]
            if aname in state["adsets"]:
                aid = state["adsets"][aname]
                print(f"  [skip] adset '{aname}' ({aid})")
            else:
                print(f"  [create] adset '{aname}'")
                targeting = dict(adset["targeting"])
                if "publisher_platforms" not in targeting:
                    targeting.update(derive_placements(adset.get("ads", [])))
                if "geo_locations" not in targeting:
                    if brand_locale:
                        targeting["geo_locations"] = {"countries": [brand_locale["country"]]}
                        print(f"    [locale] defaulted geo_locations.countries to ['{brand_locale['country']}'] from brand.domain")
                    else:
                        raise SystemExit(
                            f"error: adset '{aname}' has no targeting.geo_locations and brand.json domain "
                            f"({brand.get('domain', '<unset>')!r}) is ambiguous — set targeting.geo_locations.countries explicitly"
                        )
                build_flexible_spec(targeting, aname)
                resolve_audience_refs(targeting, aname, state)
                apply_advantage_audience(targeting)
                adset_data = {
                    "name": aname,
                    "campaign_id": cid,
                    "daily_budget": adset["daily_budget_cents"],
                    "billing_event": adset.get("billing_event", "IMPRESSIONS"),
                    "optimization_goal": adset["optimization_goal"],
                    "bid_strategy": adset.get("bid_strategy", "LOWEST_COST_WITHOUT_CAP"),
                    "targeting": json.dumps(targeting),
                    "status": adset.get("status", "PAUSED"),
                }
                if "destination_type" in adset:
                    adset_data["destination_type"] = adset["destination_type"]
                if "attribution_spec" in adset:
                    adset_data["attribution_spec"] = json.dumps(adset["attribution_spec"])
                if adset.get("optimization_goal") == "OFFSITE_CONVERSIONS":
                    adset_data["promoted_object"] = json.dumps({
                        "pixel_id": pixel_id,
                        "custom_event_type": adset.get("conversion_event", "LEAD"),
                    })
                res = meta.post(f"{meta.ad_account}/adsets", adset_data)
                aid = res["id"]
                state["adsets"][aname] = aid
                state_save_side_effect(state, project_root, dry_run=meta.dry_run)

            for ad in adset.get("ads", []):
                ad_name = ad["name"]
                if ad_name in state["ads"]:
                    print(f"    [skip] ad '{ad_name}' ({state['ads'][ad_name]})")
                    continue

                # 1) upload media, get hash/id
                media_ref = {}
                if ad.get("creative_type") == "image":
                    image_path = Path(ad["image_path"])
                    if not image_path.is_absolute():
                        image_path = project_root / image_path
                    key = str(image_path.relative_to(project_root))
                    if key in state["images"]:
                        h = state["images"][key]
                    else:
                        print(f"    [upload] image {key}")
                        h = meta.upload_image(str(image_path))
                        state["images"][key] = h
                        state_save_side_effect(state, project_root, dry_run=meta.dry_run)
                    media_ref["image_hash"] = h
                elif ad.get("creative_type") == "video":
                    video_path = Path(ad["video_path"])
                    if not video_path.is_absolute():
                        video_path = project_root / video_path
                    key = str(video_path.relative_to(project_root))
                    if key in state["videos"]:
                        vid = state["videos"][key]
                    else:
                        print(f"    [upload] video {key}")
                        vid = meta.upload_video(str(video_path))
                        state["videos"][key] = vid
                        state_save_side_effect(state, project_root, dry_run=meta.dry_run)
                    media_ref["video_id"] = vid
                    if ad.get("thumbnail_path"):
                        tp = Path(ad["thumbnail_path"])
                        if not tp.is_absolute():
                            tp = project_root / tp
                        tkey = str(tp.relative_to(project_root))
                        if tkey in state["images"]:
                            media_ref["image_hash"] = state["images"][tkey]
                        else:
                            th = meta.upload_image(str(tp))
                            state["images"][tkey] = th
                            media_ref["image_hash"] = th

                # 2) creative
                link_data = {
                    "link": ad["link"],
                    "message": ad.get("primary_text", ""),
                    "name": ad.get("headline", ""),
                    "description": ad.get("description", ""),
                    "call_to_action": {"type": ad.get("cta_type", "LEARN_MORE"), "value": {"link": ad["link"]}},
                    **{k: v for k, v in media_ref.items() if k == "image_hash"},
                }
                if ad.get("creative_type") == "video":
                    object_spec = {
                        "video_data": {
                            "video_id": media_ref["video_id"],
                            "message": ad.get("primary_text", ""),
                            "title": ad.get("headline", ""),
                            "link_description": ad.get("description", ""),
                            "call_to_action": {"type": ad.get("cta_type", "LEARN_MORE"), "value": {"link": ad["link"]}},
                            "image_hash": media_ref.get("image_hash"),
                        }
                    }
                else:
                    object_spec = {"link_data": link_data}

                creative_res = meta.post(f"{meta.ad_account}/adcreatives", {
                    "name": f"{ad_name}_creative",
                    "object_story_spec": json.dumps({"page_id": page_id, **object_spec}),
                })
                creative_id = creative_res["id"]
                state["creatives"][ad_name] = creative_id

                # 3) ad
                ad_res = meta.post(f"{meta.ad_account}/ads", {
                    "name": ad_name,
                    "adset_id": aid,
                    "creative": json.dumps({"creative_id": creative_id}),
                    "status": ad.get("status", "PAUSED"),
                })
                state["ads"][ad_name] = ad_res["id"]
                print(f"    [create] ad '{ad_name}' -> {ad_res['id']}")
                state_save_side_effect(state, project_root, dry_run=meta.dry_run)


def state_save_side_effect(state, project_root, dry_run=False):
    if dry_run:
        return
    state_save(project_root / ".adforge" / "state.json", state)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", help="path to campaign plan JSON")
    ap.add_argument("--dry-run", action="store_true", help="print what would happen, don't call API")
    args = ap.parse_args()

    plan_path = Path(args.plan)
    project_root = find_project_root(plan_path)
    env = {**os.environ, **load_env(project_root)}

    if not args.dry_run:
        for required in ("META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID", "META_PAGE_ID"):
            if not env.get(required):
                raise SystemExit(f"error: {required} not set (in .env or env)")

    token = env.get("META_ACCESS_TOKEN", "")
    ad_account = env.get("META_AD_ACCOUNT_ID", "act_000")
    page_id = env.get("META_PAGE_ID", "")
    pixel_id = env.get("META_PIXEL_ID", "")

    plan = json.loads(plan_path.read_text())
    state_path = project_root / ".adforge" / "state.json"
    state = state_load(state_path)

    meta = Meta(token, ad_account, dry_run=args.dry_run)
    deploy(plan, state, meta, project_root, page_id, pixel_id)
    if not args.dry_run:
        state_save(state_path, state)
    print("\ndone.")


if __name__ == "__main__":
    main()
