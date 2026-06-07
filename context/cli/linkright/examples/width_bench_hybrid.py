"""Real local-model hybrid width benchmark, run where the Oracle VPS is reachable.

Wires the real local-model candidate generator into the same corpus as
width_bench.py and reports band-hit rate and true latency (p50, p95). Use it to
confirm the locked target (p95 under 8s per bullet) and to compare local models,
e.g. the LFM2 default against an LFM variant.

Prereqs:
  - ORACLE_BACKEND_URL and ORACLE_BACKEND_SECRET set in the environment.
  - Each model you benchmark must be pulled in the VPS Ollama and allow-listed in
    the oracle-backend /lifeos/rewrite route. The backend default (LFM2) needs no
    model arg.

Run (from context/cli/linkright):
  PYTHONPATH=src python examples/width_bench_hybrid.py
  # compare specific models (empty string = backend default LFM2):
  PYTHONPATH=src python examples/width_bench_hybrid.py "" "hf.co/LiquidAI/lfm2.5-1.2b-instruct"
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                  # width_bench
sys.path.insert(0, os.path.join(_HERE, "..", "src"))      # linkright package

from width_bench import run  # noqa: E402
from linkright.tools.width_llm import make_oracle_llm_fn  # noqa: E402


def _bench_model(model):
    tag = model or "backend default (LFM2)"
    fn = make_oracle_llm_fn(timeout_s=8.0, n=3, model=model)
    # Warm once so the first bullet does not pay cold-start (8-12s).
    try:
        fn("Cut churn <b>18%</b>",
           type("M", (), {"status": "TOO_SHORT", "fill_percentage": 12})())
        print(f"warmed {tag}")
    except Exception as e:
        print(f"warmup skipped for {tag}: {e}")
    run(llm_fn=fn, label=f"hybrid, model = {tag}")


if __name__ == "__main__":
    if not os.environ.get("ORACLE_BACKEND_URL"):
        print("Set ORACLE_BACKEND_URL and ORACLE_BACKEND_SECRET first.")
        sys.exit(1)
    # Models to compare. argv overrides; "" means the backend default (LFM2).
    models = sys.argv[1:] or [""]
    for m in models:
        _bench_model(m or None)
