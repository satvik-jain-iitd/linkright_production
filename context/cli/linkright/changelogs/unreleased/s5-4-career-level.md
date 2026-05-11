## [type: Changed]
<!-- pr: TBD -->
- **S5.4 (Career level → pure deterministic):** Removed LLM retry loop for career_level in step_07. Classification now always uses `_bucket_from_years(total_years)` — zero run-to-run variance, one fewer API round-trip on mis-classified inputs.
