# Root-Cause Analysis — 9 Quality Gaps

## Priority Matrix

| Gap | Severity | Fix Effort | Priority |
|-----|----------|------------|----------|
| 1. Contrast field name | Critical (silent no-op) | 5 min | P0 |
| 2. Keyword substring | High (inflated scores) | 30 min | P0 |
| 3. Silent width fail | High (visual defects) | 1 hr | P1 |
| 7. No synonym retry | High (systemic overflow) | 2 hr | P1 |
| 9. Post-LLM validation | High (data integrity) | 3 hr | P1 |
| 6. No Pydantic validation | Medium (silent degradation) | 2 hr | P2 |
| 4. Quality judge module | Medium (incomplete grading) | 3 hr | P2 |
| 8. Vector search quality | Medium (wasted context) | 1 hr | P2 |
| 5. No state logging | Low (debugging only) | 2 hr | P3 |

## Gap Details

### 1. Contrast Check Never Fires (P0)
- **Root cause:** orchestrator.py:1212 reads `passes_aa_normal` but tool returns `passes_wcag_aa_normal_text`
- **Fix:** Change key name, change default from True to False (fail-safe)
- **Verify:** Test with #FFFF00 (yellow on white, ratio ~1.07), assert warning generated

### 2. Keyword False Positives (P0)
- **Root cause:** `if keyword in text_lower` — substring match in score_bullets.py:182 + orchestrator:1251
- **Fix:** `re.search(r'\b' + re.escape(keyword) + r'\b', text_lower)`
- **Verify:** "Reengineered" should NOT match "engineer"

### 3. Phase 5 Silent Width Failures (P1)
- **Root cause:** orchestrator.py:1098-1103 keeps failing bullets with no warning
- **Fix:** Track `still_failing` list, store in ctx.stats, add Phase 7 warning
- **Verify:** Feed 115% fill bullet, assert width_failures in stats

### 4. Missing Quality Judge Module (P2)
- **Root cause:** CLI has standalone quality_judge.py; web has inline partial checks
- **Fix:** Create worker/app/tools/quality_judge.py, port all 6 checks + QualityReport
- **Verify:** Feed known bullets, assert grade matches CLI for same input

### 5. No State Logging (P3)
- **Root cause:** No save_state() between phases; only timings logged
- **Fix:** Add _save_checkpoint() after each phase, store in Supabase JSONB
- **Verify:** Full pipeline run → assert 8 checkpoint rows exist

### 6. No Pydantic Validation (P2)
- **Root cause:** _parse_json() only does json.loads(); no schema validation
- **Fix:** Define Phase1Response, Phase4AResponse, Phase4CResponse, Phase5Response models
- **Verify:** Missing field → assert ValidationError raised

### 7. No Synonym Retry Loop (P1)
- **Root cause:** Web never calls suggest_synonyms despite importing it
- **Fix:** After 2nd pass failures, call suggest_synonyms per bullet, make 3rd targeted LLM call
- **Verify:** 87% fill bullet → assert synonyms called with direction="expand"

### 8. Vector Search Quality (P2)
- **Root cause:** No dedup in hybrid_search(), no empty filtering
- **Fix:** Normalize + dedup chunks, filter empties, log warnings
- **Verify:** 3 identical chunks + 2 empty → assert 1 unique, 0 empty

### 9. Post-LLM Validation Missing (P1)
- **Root cause:** Phase 4A/4C/1+2 accept raw LLM output without structure checks
- **Fix:** Validate paragraph length (150-500), verb uniqueness, `<b>` tags, hex colors
- **Verify:** 50-char paragraph → assert rejected; invalid hex → assert fallback
