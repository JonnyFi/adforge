#!/usr/bin/env python3
"""Meta adapter — pull insights for all active adsets/ads, print report.

Usage:
    python3 adapters/meta/review.py [--days 7] [--level adset|ad]

Reads state file to know which IDs to query. Writes JSON report to
.adforge/reports/<iso-timestamp>.json in addition to stdout.
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import bearer_headers, redact_body

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


def get_insights(token, obj_id, days):
    date_preset = {1: "yesterday", 7: "last_7d", 14: "last_14d", 28: "last_28d", 30: "last_30d"}.get(days, "last_7d")
    params = {
        "fields": "impressions,reach,spend,clicks,ctr,cpm,cpc,actions,action_values",
        "date_preset": date_preset,
    }
    r = requests.get(f"{API}/{obj_id}/insights", params=params, headers=bearer_headers(token))
    if r.status_code >= 400:
        return {"error": redact_body(r.text)}
    return r.json().get("data", [{}])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--level", choices=["adset", "ad"], default="adset")
    args = ap.parse_args()

    project_root = find_project_root(Path.cwd())
    env = {**os.environ, **load_env(project_root)}
    token = env.get("META_ACCESS_TOKEN")
    if not token:
        raise SystemExit("META_ACCESS_TOKEN not set")

    state_path = project_root / ".adforge" / "state.json"
    if not state_path.exists():
        raise SystemExit("no state file — nothing has been deployed yet")
    state = json.loads(state_path.read_text())

    targets = state["adsets"] if args.level == "adset" else state["ads"]
    if not targets:
        print(f"no {args.level}s in state")
        return

    print(f"adforge review — last {args.days}d — {len(targets)} {args.level}s\n")
    rows = []
    for name, mid in targets.items():
        ins = get_insights(token, mid, args.days)
        if "error" in ins:
            print(f"  [err] {name}: {ins['error'][:120]}")
            continue
        imp = int(ins.get("impressions", 0))
        spend = float(ins.get("spend", 0))
        ctr = float(ins.get("ctr", 0))
        cpm = float(ins.get("cpm", 0))
        cpc = float(ins.get("cpc", 0))
        # Meta's `lead` is the top-level aggregator — it already rolls up
        # `onsite_conversion.lead_grouped` and `offsite_conversion.fb_pixel_lead`.
        # Summing all three double/triple-counts every lead.
        leads = 0
        for a in ins.get("actions", []):
            if a.get("action_type") == "lead":
                leads += int(a.get("value", 0))
        rows.append({
            "name": name, "id": mid, "impressions": imp, "spend_eur": spend,
            "ctr_pct": ctr, "cpm_eur": cpm, "cpc_eur": cpc, "leads": leads,
            "cost_per_lead_eur": (spend / leads) if leads else None,
        })

    rows.sort(key=lambda r: r["spend_eur"], reverse=True)
    print(f"{'name':<40} {'spend':>8} {'impr':>8} {'ctr%':>6} {'cpm':>6} {'leads':>6} {'cpl':>6}")
    print("-" * 84)
    for r in rows:
        cpl = f"{r['cost_per_lead_eur']:.2f}" if r["cost_per_lead_eur"] else "—"
        print(f"{r['name'][:40]:<40} {r['spend_eur']:>8.2f} {r['impressions']:>8} "
              f"{r['ctr_pct']:>6.2f} {r['cpm_eur']:>6.2f} {r['leads']:>6} {cpl:>6}")

    reports_dir = project_root / ".adforge" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = reports_dir / f"review-{args.level}-{args.days}d-{ts}.json"
    out.write_text(json.dumps({"generated_at": ts, "level": args.level, "days": args.days, "rows": rows}, indent=2))
    print(f"\nreport: {out.relative_to(project_root)}")


if __name__ == "__main__":
    main()
