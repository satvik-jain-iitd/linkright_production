# Width optimizer, rules-first short-circuit (latency fix)

## Fixed

- The optimizer called the local model on every below-ideal bullet, even ones rules already placed in the ok band (90-100). On the VPS that added 5 to 15 seconds per bullet for zero band gain, minutes across a full resume, in the regime that is most of production.
- `optimize_bullet` now runs a rules-only pass first. If rules land the bullet in the ok band and content-clean, it returns immediately, no network. The local model is spent only when rules genuinely cannot reach the band (true short fragments), where the two-phase overshoot-then-compress still runs. This matches the documented intent.

## Notes

- Verified: the realistic regime makes zero model calls (a model that raises on call is never hit) and stays 8 of 8 at sub-millisecond latency; a 12%-fill fragment still escalates to the model and reaches the ideal band. Caught by the real-VPS re-bench, which the mock could not have surfaced.
