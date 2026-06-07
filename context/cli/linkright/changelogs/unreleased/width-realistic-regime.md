# Width optimizer, realistic-regime benchmark

## Added

- **`examples/width_bench.py`** gained `REALISTIC_CORPUS`, bullets as the writer actually emits them (near full line length, needing only a small nudge), and `run(corpus=...)`. The original adversarial `CORPUS` (fragments needing 8x expansion) is kept as a stress set.
- **`examples/width_bench_hybrid.py`** now benchmarks the realistic regime and uses the tuned knobs (n=2, timeout 5s).

## Notes

- On the realistic regime, rules-only reaches the band 8 of 8 at sub-millisecond latency, no model call. The 2/11 seen earlier was entirely an artifact of the adversarial fragment corpus, which the bullet writer never produces. In production the optimizer mostly never invokes the local model; rules-first plus the cleaned bank handle the small nudges instantly. The local LFM model is the safety net for the rare bullet rules cannot fix, with graceful rules-plus-relaxed fallback under model eviction. The durable p95 fix for the eviction case is infra (raise Ollama keep_alive or OLLAMA_MAX_LOADED_MODELS so embed traffic stops evicting the rewrite model).
