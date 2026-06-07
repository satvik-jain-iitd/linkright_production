# Bullet writer, local-first hybrid width tuning (W4)

## Changed

- **`agents/bullet_writer.py`**: the per-bullet width tuning now runs through `optimize_bullet` (the hybrid optimizer) instead of the Claude Sonnet revise loop. Candidates come from rule swaps first, then the local VPS gemma3:1b when rules cannot reach the band; the deterministic measurer, the content gate, and a metric-integrity guard pick the winner, never regressing below the input. On any Oracle failure it falls back to rules plus accept-relaxed, fully local, no cloud. The initial XYZ bullet is still written by Claude; only the width-and-content tuning moved local.

## Notes

- Removes the cloud round-trips that the old three-attempt revise loop spent on width. Latency target is p95 under 8s per bullet, verified on the VPS via `examples/width_bench_hybrid.py`.
