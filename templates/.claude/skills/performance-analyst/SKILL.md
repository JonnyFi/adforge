---
name: performance-analyst
description: Backend skill — interpret Meta insights JSON report and recommend actions. Used by review-performance.
---

# performance-analyst

Read a report from `.adforge/reports/review-*.json` and turn it into a short recommendation set.

## Input

- The latest review JSON (path passed by caller)
- Previous review if one exists (for delta)
- `.adforge/state.json` for context (which campaigns these are in)

## Method

1. **Account benchmarks.** Compute median CPM, CTR, CPC, CPL across all ads. Flag anything >2× median on cost or <0.5× median on engagement.
2. **Outlier classification.** For each flagged row:
   - High-spend-no-leads → pause candidate
   - Low-CPL below target → scale candidate
   - Flat CTR + high frequency → refresh candidate
3. **Budget health.** Sum spend vs. daily-budget × days. If underpacing <60%, flag as "budget not reaching" — targeting or bid issue.
4. **Delta.** If previous report exists, note what changed (new ads, paused ads, meaningful CTR/CPM shifts).

## Output

Maximum 5 recommendations. Each is one sentence, action-first:

- "Pause `<ad-name>` — €<spend> spent, 0 leads, CPM 3.2× median."
- "Scale `<adset-name>` to <budget> cents/day — CPL €<x>, 40% below target."
- "Refresh `<ad-name>` — live <N> days, CTR down from <x> to <y>."

End with a plain-language summary: "Overall: <what's working> / <what's not> / <one next move>."
