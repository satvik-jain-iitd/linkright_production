## [type: Added]
<!-- pr: TBD -->

- **S4.4 (Success box quality signals):** After `linkright resume tailor` completes, the success
  box now shows two quality signals alongside the PDF path and duration:
  `JD Coverage` (X/Y reqs covered, %) read from `artifacts/06_role_scores.json`, and
  `Width hits` (X/Y bullets in 108-120 char target band, %) read from the `width_poc` block
  in `artifacts/16_telemetry.json`. Values below 80% render in coral (#FF5733) as a visual
  warning. Both fields are omitted gracefully when the artifact files are absent or malformed
  (no crash). Adds `_read_quality_metrics()` and `_fmt_metric_value()` helpers to
  `resume/cli.py`. Tests in `tests/test_success_box.py` (17 passing: AC1-AC4).
