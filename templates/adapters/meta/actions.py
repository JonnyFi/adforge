#!/usr/bin/env python3
"""Meta adapter — pause / resume / scale / delete actions on state-tracked objects.

Usage:
    python3 adapters/meta/actions.py pause  --ad <name>
    python3 adapters/meta/actions.py resume --adset <name>
    python3 adapters/meta/actions.py scale  --adset <name> --daily-budget-cents 3000
    python3 adapters/meta/actions.py delete --ad <name>
"""
import argparse
import json
import os
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


def resolve_id(state, kind, name):
    bucket = {"ad": "ads", "adset": "adsets", "campaign": "campaigns"}[kind]
    if name not in state[bucket]:
        raise SystemExit(f"error: no {kind} named '{name}' in state")
    return state[bucket][name]


def api_post(token, obj_id, data):
    data = dict(data)
    data["access_token"] = token
    r = requests.post(f"{API}/{obj_id}", data=data)
    if r.status_code >= 400:
        raise RuntimeError(f"POST {obj_id} failed {r.status_code}: {r.text}")
    return r.json()


def api_delete(token, obj_id):
    r = requests.delete(f"{API}/{obj_id}", params={"access_token": token})
    if r.status_code >= 400:
        raise RuntimeError(f"DELETE {obj_id} failed {r.status_code}: {r.text}")
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["pause", "resume", "scale", "delete"])
    ap.add_argument("--ad")
    ap.add_argument("--adset")
    ap.add_argument("--campaign")
    ap.add_argument("--daily-budget-cents", type=int)
    args = ap.parse_args()

    kind_name = next(((k, getattr(args, k)) for k in ("ad", "adset", "campaign") if getattr(args, k)), None)
    if not kind_name:
        raise SystemExit("specify --ad, --adset, or --campaign")
    kind, name = kind_name

    project_root = find_project_root(Path.cwd())
    env = {**os.environ, **load_env(project_root)}
    token = env.get("META_ACCESS_TOKEN")
    if not token:
        raise SystemExit("META_ACCESS_TOKEN not set")
    state = json.loads((project_root / ".adforge" / "state.json").read_text())
    obj_id = resolve_id(state, kind, name)

    if args.action == "pause":
        api_post(token, obj_id, {"status": "PAUSED"})
        print(f"paused {kind} '{name}' ({obj_id})")
    elif args.action == "resume":
        api_post(token, obj_id, {"status": "ACTIVE"})
        print(f"resumed {kind} '{name}' ({obj_id})")
    elif args.action == "scale":
        if kind != "adset":
            raise SystemExit("scale only applies to --adset")
        if not args.daily_budget_cents:
            raise SystemExit("--daily-budget-cents required for scale")
        api_post(token, obj_id, {"daily_budget": args.daily_budget_cents})
        print(f"scaled adset '{name}' to {args.daily_budget_cents / 100:.2f} EUR/day")
    elif args.action == "delete":
        api_delete(token, obj_id)
        bucket = {"ad": "ads", "adset": "adsets", "campaign": "campaigns"}[kind]
        del state[bucket][name]
        (project_root / ".adforge" / "state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False))
        print(f"deleted {kind} '{name}' ({obj_id})")


if __name__ == "__main__":
    main()
