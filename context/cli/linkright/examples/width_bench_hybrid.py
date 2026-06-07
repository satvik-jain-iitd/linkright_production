"""Real local-model hybrid width benchmark, run where the Oracle VPS is reachable.

This wires the real gemma3:1b candidate generator into the same corpus as
width_bench.py and reports band-hit rate and true latency (p50, p95). Use it to
confirm the locked target: p95 under 8s per bullet.

Prereqs:
  - ORACLE_BACKEND_URL and ORACLE_BACKEND_SECRET set in the environment.
  - gemma3:1b pulled on the VPS Ollama (otherwise /lifeos/rewrite 503).

Run (from context/cli/linkright):
  PYTHONPATH=src python examples/width_bench_hybrid.py
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                  # width_bench
sys.path.insert(0, os.path.join(_HERE, "..", "src"))      # linkright package

from width_bench import run  # noqa: E402
from linkright.tools.width_llm import make_oracle_llm_fn  # noqa: E402


if __name__ == "__main__":
    if not os.environ.get("ORACLE_BACKEND_URL"):
        print("Set ORACLE_BACKEND_URL and ORACLE_BACKEND_SECRET first.")
        sys.exit(1)
    # Warm the model once so the first bullet does not pay cold-start (8-12s).
    try:
        make_oracle_llm_fn()("Cut churn <b>18%</b>", type("M", (), {"status": "TOO_SHORT", "fill_percentage": 12})())
        print("warmed local model")
    except Exception as e:
        print("warmup skipped:", e)

    llm_fn = make_oracle_llm_fn(timeout_s=8.0, n=3)
    run(llm_fn=llm_fn, label="hybrid (real gemma3:1b on Oracle VPS)")
