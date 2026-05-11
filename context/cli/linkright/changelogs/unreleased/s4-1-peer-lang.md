## [type: Added]
<!-- pr: -->

- **S4.1 (Peer-vs-applicant language bank):** Added seniority-tone calibration for
  step_10 bullet generation. New `peer_applicant_bank.yaml` (86 phrase entries across
  3 bands: junior/mid/senior) and `peer_applicant.py` lib map `career_level` → tone
  band and inject a structured verb-guidance section into the PHASE_4A_VERBOSE_SYSTEM
  prompt. Senior/executive candidates now get peer-to-panel verbs (co-led, championed,
  evangelized); junior candidates get strong-contributor verbs (shipped, built, drove).
  Fabrication safeguard preserved: guidance instructs LLM to use verbs only where
  evidence naturally supports it.
