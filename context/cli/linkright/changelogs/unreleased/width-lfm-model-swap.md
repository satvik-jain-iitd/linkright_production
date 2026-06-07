# Width optimizer, swappable local model + LFM comparison

## Changed

- **`llm/oracle.py`** `oracle_rewrite` gained a `model` argument, passed through to `/lifeos/rewrite`. Default (None) uses the backend's configured local model, now LFM2 (Liquid AI), not gemma3:1b.
- **`tools/width_llm.py`** `make_oracle_llm_fn` accepts `model`, so the candidate generator can target a specific allow-listed local model. Stale gemma3:1b references corrected to reflect the LFM2 default.
- **`examples/width_bench_hybrid.py`** can now benchmark several local models in one run, e.g. the LFM2 default against an LFM variant, reporting band-hit and p50/p95 latency per model so the best one can be picked.

## Notes

- The hybrid design makes the generator model a pure swap: the deterministic measurer, content gate, and metric guard enforce quality regardless of which small model proposes the text, so trying LFM variants carries no correctness risk.
- To benchmark a non-default model it must be pulled in the VPS Ollama and allow-listed in the oracle-backend `/lifeos/rewrite` route.
