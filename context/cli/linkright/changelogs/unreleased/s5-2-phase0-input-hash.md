## [type: Added]
<!-- pr: TBD -->
- **S5.2 Phase 0 (input hash instrumentation):** `16_telemetry.json` now records `input_hash` (sha256 of resume bytes + JD text + pipeline version) and `pipeline_version` per run. After 1 week of passive collection, hit rate is measured to gate Phase 1 (actual output caching). No behaviour change for users.
