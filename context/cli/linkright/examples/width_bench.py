"""Width optimizer benchmark, realistic corpus.

Runs the hybrid bullet width optimizer over realistic resume bullets and reports
how many reach the width band, the path taken (rules / llm / relaxed), metric
integrity, and latency. Pass an llm_fn to measure the hybrid lift over rules-only.

Usage:
  python examples/width_bench.py                 # rules-only baseline
  # W3 wires a real local-model llm_fn and re-runs this against the VPS.
"""
from __future__ import annotations

import statistics
import time
from collections import Counter

from linkright.data.default_template import DEFAULT_TEMPLATE_CONFIG as CFG
from linkright.tools.width_optimizer import optimize_bullet, _measure

# Realistic corpus, real projects, <b> metrics, deliberately varied widths.
CORPUS = [
    # too-long (need trim)
    "Led the implementation of a comprehensive cross-functional onboarding transformation that reduced driver churn by <b>18%</b> across the Walmart Spark Driver program",
    "Was responsible for the development of data infrastructure resulting in significant improvement in Sprinklr CRR reporting performance for stakeholders",
    "Orchestrated the implementation of approximately <b>40</b> experiments in collaboration with the growth team subsequently driving retention improvement",
    # too-short (need expand, rules cannot add content)
    "Cut churn <b>18%</b>",
    "Ran <b>40</b> A/B tests",
    "Built the <b>CRR</b> tool",
    "Set up Navii cohorts",
    # near-ideal already
    "Reduced driver churn by <b>18%</b> by redesigning the Walmart Spark onboarding flow across <b>100K+</b> drivers",
    "Drove <b>$2.3M</b> in annual savings by owning the Sprinklr CRR data pipeline across <b>4</b> teams",
    # edge: weak opener + filler (content gate forces revise even if width ok)
    "Responsible for various onboarding tasks that successfully improved the <b>Spark</b> driver experience overall here",
    # edge: no emphasis
    "Reduced onboarding time from 14 days to 6 days by redesigning the driver setup wizard end to end",
]


def run(llm_fn=None, label="rules-only"):
    rows = []
    lat = []
    for b in CORPUS:
        before = _measure(b, CFG)
        t = time.perf_counter()
        r = optimize_bullet(b, CFG, llm_fn=llm_fn)
        dt = (time.perf_counter() - t) * 1000
        lat.append(dt)
        rows.append((before.fill_percentage, r.fill, r.status, r.path, r.candidates_tried, dt))

    print(f"\n=== width benchmark: {label} ===")
    print(f"{'before':>7} {'after':>6}  {'status':<8} {'path':<8} {'cand':>4} {'ms':>8}")
    for fb, fa, st, pa, cn, dt in rows:
        print(f"{fb:7.1f} {fa:6.1f}  {st:<8} {pa:<8} {cn:>4} {dt:8.1f}")

    c = Counter(r[2] for r in rows)
    landed = c["ideal"] + c["pass"]
    print(f"\nstatus mix: {dict(c)}")
    print(f"reached band (ideal+pass): {landed}/{len(rows)}  relaxed: {c['relaxed']}  failed: {c['failed']}")
    print(f"latency p50={statistics.median(lat):.1f}ms  p95={sorted(lat)[int(len(lat)*0.95)-1]:.1f}ms  max={max(lat):.1f}ms")
    return rows


if __name__ == "__main__":
    run(llm_fn=None, label="rules-only baseline")
