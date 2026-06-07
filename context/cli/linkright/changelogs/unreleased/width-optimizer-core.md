# Hybrid width optimizer, core + baseline (W2)

## Added

- **`tools/width_optimizer.py`**: the generate-then-verify bullet width optimizer. Width is measured deterministically; candidates come from rule swaps first (and an optional injectable `llm_fn` for the local model in W3); the measurer plus the content gate plus a metric-integrity guard pick the winner. The constraint is always enforced by code, never by the model. Fallback chain is fully local: rules, then accept-relaxed (85 to 105 percent).
- **`examples/width_bench.py`**: a realistic benchmark over real-project bullets across too-short, too-long, near-ideal, and edge cases. Reports band-hit rate, path taken, metric integrity, and latency. Reused in W3 with a real local-model `llm_fn`.

## Notes

- Baseline, rules only: 1 of 11 bullets reach the band, p95 1.6ms. Short fragments cannot be fixed by swaps (rules can only swap words, not add grounded detail), and several trims are not in the bank. This quantifies why the local model is needed for the hard majority, and confirms the rules-first path is essentially free so the model is only called when rules cannot reach the band.
