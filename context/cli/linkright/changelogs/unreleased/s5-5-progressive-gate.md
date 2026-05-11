## [type: Added]
<!-- pr: TBD -->
- **S5.5 (Progressive validation gate):** Added `_should_regenerate()` BRS threshold gate (default 0.60, env: `LR_BRS_THRESHOLD`) between fabrication guard and step_12. Bullets below threshold are flagged `_below_threshold`; success box warns "N bullets below quality threshold" when present.
