# Width optimizer, local-model candidates (W3)

## Added

- **`tools/width_llm.py`**: `make_oracle_llm_fn`, a local-model candidate generator for the width optimizer. One call to the VPS gemma3:1b (`/lifeos/rewrite`) returns up to three width-targeted rewrites; the optimizer then measures, gates, and picks. On any Oracle failure it returns nothing, so the optimizer falls back to rules plus accept-relaxed, fully local. The model proposes language, code enforces width, numbers, and banned words.
- **`examples/width_bench_hybrid.py`**: the real-VPS benchmark runner, warms the model then reports band-hit rate and true p50/p95 latency against the locked p95-under-8s target.

## Changed

- **`tools/width_optimizer.py`** selection rewritten to track a global best and never return a bullet worse than the input. Candidates compete on content-clean, then in-band, then closeness to the ideal midpoint.

## Notes

- Mock-local proof on the realistic corpus: band-hit rose from 1 of 11 (rules only) to 10 of 11. A deliberately bad candidate (banned word plus a changed metric) was filtered by the content gate and metric guard, confirming a weak 1b is safe behind the verifier. Real gemma3:1b latency and quality are measured via `width_bench_hybrid.py` on the VPS.
