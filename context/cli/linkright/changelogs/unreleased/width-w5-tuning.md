# Width optimizer, candidate quality + speed tuning (W5)

## Changed

- **`tools/width_llm.py`**: the rewrite prompt is now direction-specific. For a too-short bullet it asks the model to lengthen with method, context, or scope in words and explicitly forbids adding any new number, so legitimate expansions stop being rejected by the metric-integrity guard (the main reason real small-model candidates were not landing). For a too-long bullet it asks to cut filler while keeping every number and `<b>` tag.
- **`agents/bullet_writer.py`**: width tuning now requests `model="LiquidAI/lfm2.5-1.2b-instruct:latest"`, `n=2`, `timeout_s=5.0`. The 1.2b variant reloads cold in ~1.5s versus the 2.6B's 16-33s, so its p95 tail on the shared VPS is far shorter; the extra candidate did not move band-hit, so n drops to 2; 5s fails fast on an eviction instead of dragging the tail.
- **`tools/width_optimizer.py`**: `optimize_bullet` is now cached by bullet and bands, so an identical bullet skips recompute and a repeat model call.

## Notes

- The bench's adversarial fragments understate production band-hit; real bullets reach the optimizer near full length and need small nudges, not 8x expansion. The direction-specific prompt plus the realistic regime should be re-measured on the VPS via `width_bench_hybrid.py`. Batching candidates across bullets in one call is a further latency optimization, deferred until the re-bench confirms the band-hit lift.
