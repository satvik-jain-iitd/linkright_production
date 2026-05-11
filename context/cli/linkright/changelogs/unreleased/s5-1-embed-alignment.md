## [type: Added]
<!-- pr: TBD -->
- **S5.1 (Embedding-based JD-bullet alignment):** step_11_rank now blends BRS score (70%) with Oracle nomic-embed-text cosine alignment (30%) when jd_req_texts available. Req texts are auto-derived from jd_requirement_clusters canonical_labels when not provided explicitly. Each bullet receives a `_alignment_score` field for telemetry. Deterministic, semantically richer ranking with no extra API calls (Oracle local). Graceful fallback to BRS-only when Oracle unreachable. 7 new tests in tests/test_jd_alignment_embedding.py (all pass).
