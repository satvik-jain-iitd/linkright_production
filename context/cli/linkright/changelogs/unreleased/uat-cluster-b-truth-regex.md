### Truth Engine — regex pre-extraction for high-confidence contact fields (UAT #13)

**Cluster B-truth-engine — fix verification (bug #13).**

- Added `linkright/profile/regex_extract.py` as the single source of truth for
  deterministic email + phone extraction. Exports `extract_email`,
  `extract_phone`, `extract_email_phone`, and `reconcile_contact`.
- Wired into the resume pipeline at three points:
  1. `step_01_parse_resume` — pre-fills `contact_info` from raw resume text
     before any LLM is asked (also stamps a `contact_info_regex` provenance
     key that is never overwritten downstream).
  2. `step_07_phase_1_2` — surfaces regex hits to the LLM via a
     `qa_context` block in the PHASE_1_2 user prompt so the model is biased
     toward the deterministic values; post-LLM call uses `reconcile_contact`
     so regex wins on disagreement.
  3. `profile/pipeline._extract_contact_from_text` — uses the same shared
     regexes during `linkright profile create`.
- Conservative regexes — date shapes (`2024-03-15`, `15/03/1990`), bare
  4-digit years, and 5-digit ZIPs are rejected as phone candidates; URL
  userinfo (`http://name@example.com`) and numeric TLDs are rejected as
  emails.
- Disagreement records (`parsed["contact_disagreements"]`) flow through
  the existing verifier loop so the user can confirm/edit when LLM and
  regex disagreed at parse time.
- New test module `tests/test_uat_cluster_b_truth.py` (35 cases) covers
  happy paths, Indian + US phone formats, false-positive guards,
  reconciliation rules, and orchestrator wiring.
