---
name: review-performance
description: Pull Meta insights, summarise performance, recommend actions, offer to execute them. Invoked from hub.
---

# review-performance

Two-stage flow. First report, then actions.

## 1. Report

Ask the user for a time window (default 7 days) and level (adset or ad, default adset).

Run `python3 adapters/meta/review.py --days <N> --level <level>`. The script writes a JSON report and prints a table.

Load `performance-analyst` skill to interpret: which adsets are carrying spend, which are outliers (good or bad), what changed vs. the previous review.

## 2. Actions

Present 3–5 concrete recommendations. Examples:

- "Pause ad X — CPM is 3.2× the account average with no leads."
- "Scale adset Y to 3000 cents/day — CPL is 40% below target."
- "Refresh ad Z — 14 days active, frequency > 3.5, CTR dropping."

For each, ask: "Do this? [y/n]". Multi-select:

- `y` — execute via `adapters/meta/actions.py`
- `refresh` — hand off to `add-creative` with context pre-filled

Never execute actions without per-item approval.
