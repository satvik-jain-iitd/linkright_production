# Width optimizer, two-phase overshoot then compress (W6)

## Changed

- **`tools/width_optimizer.py`**: a bullet that starts below the band is now tuned in two phases. Phase 1 expands it to a loose overshoot band (100 to 110 percent), an easy target the model can hit by writing a little long. Phase 2 deterministically compresses that down to the ideal 95 to 100. This follows the reliable-direction asymmetry: compression is deterministic and metric-safe, expansion is not, so converting "expand to exact" into "expand generously, then trim precisely" lands far more reliably. A bullet already in or over the band takes a single compress-to-ideal pass. Refactored the core loop into a reusable `_tune` toward any target band; never regresses below the original; metric integrity is checked against the true original, not the overshoot intermediate.
- **`tools/width_llm.py`**: the expand prompt now asks the model to overshoot into the 100 to 110 range, since writing a little long is the easy half of the two-phase.

## Notes

- Verified: a 12%-fill fragment now reaches the ideal band via overshoot then compress, where a single direct-expand pass could not. The realistic regime stays 8 of 8 with no regression.
