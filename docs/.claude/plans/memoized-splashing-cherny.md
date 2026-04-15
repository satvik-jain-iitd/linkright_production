# Nugget Data Quality Fix — Retrieval & Resume Generation Readiness

## Context

232 career_nuggets in Supabase have severe data quality issues that cause retrieval failures during resume generation. The hybrid retrieval system (BM25 on `answer` + vector cosine on `embedding`) scopes by `company` field and groups output as `## Company: {company} | Role: {role}`. When these fields are NULL or answers aren't self-contained, retrieval either misses nuggets entirely or feeds broken context to the LLM.

**Root causes**: (1) LLM ignores extraction rules on 50-97% of nuggets, (2) `event_date` column is type DATE but extractor passes "YYYY-MM" strings which silently fail, (3) no post-extraction validation exists, (4) no dedup across extraction runs.

---

## Issue Severity by Retrieval Impact

| # | Issue | Scope | Impact |
|---|-------|-------|--------|
| 1 | **Answers not self-contained** — 97% of work answers lack company+role+date | 225/232 | BM25 on `answer` column can't find company-related nuggets |
| 2 | **Company NULL on 52%** — 25 work_experience violate schema | 120/232 | `WHERE company='AmEx'` skips these entirely |
| 3 | **Role NULL on 74%** — 64 work_experience violate schema | 171/232 | Phase 4A LLM sees `Role: null` header |
| 4 | **event_date = 0%** — DATE column rejects "YYYY-MM" strings silently | 232/232 | No chronological ordering possible |
| 5 | **20 exact duplicates** + 11 near-dupes | 40 rows | Waste retrieval slots (limit=8/company) |
| 6 | **34 section_type NULL** — Layer A constraint violated | 34/232 | Dashboard filtering broken |
| 7 | **Tags malformed** — bracket artifacts `[family` | 232 | Tag queries fail |
| 8 | **Company name inconsistency** — "American Express" vs "Amex" | 2 variants | Exact-match retrieval misses variant |
| 9 | **People field 0%** | 232/232 | Low priority |
| 10 | **resume_relevance < 0.5** on 42 nuggets | 42/232 | Filtered out of unscoped retrieval |

---

## Execution Plan (5 Phases)

### Phase A: Zero-Cost Fixes (SQL + small code changes, no LLM/API cost)

**A1. Fix malformed tags** — SQL script
```sql
UPDATE career_nuggets SET tags = (
  SELECT array_agg(regexp_replace(regexp_replace(elem, '^\[', ''), '\]$', ''))
  FROM unnest(tags) AS elem
) WHERE EXISTS (SELECT 1 FROM unnest(tags) AS elem WHERE elem LIKE '[%' OR elem LIKE '%]');
```

**A2. Deduplicate exact duplicates** — SQL script
- `ROW_NUMBER() OVER (PARTITION BY user_id, nugget_text ORDER BY created_at)`
- Tag rows with `row_number > 1` as `duplicate_archived` (no DELETE)

**A3. Fix `format_nuggets_for_llm()` NULL handling**
- File: `worker/app/tools/hybrid_retrieval.py:414`
- Replace `{r.company}` with `{r.company or "Unknown"}`, same for role

**A4. Add duplicate exclusion to retrieval queries**
- File: `worker/app/tools/hybrid_retrieval.py` — filter `duplicate_archived` tag in both `_bm25_query()` and `_vector_query()`
- Update `match_career_nuggets` RPC to exclude archived

**A5. Add BM25 fallback to `nugget_text` column**
- File: `worker/app/tools/hybrid_retrieval.py:136` — if BM25 on `answer` returns 0 results, retry on `nugget_text`
- New migration: `CREATE INDEX idx_nuggets_fts_nugget_text ON career_nuggets USING gin(to_tsvector('english', nugget_text));`

**A6. Fix event_date type coercion in extractor**
- File: `worker/app/tools/nugget_extractor.py:243` (`_nugget_to_row`)
- Convert "2022" → "2022-01-01", "2022-06" → "2022-06-01" before DB insert
- This fixes the root cause of 0% event_date population for ALL future extractions

---

### Phase B: Metadata Backfill (LLM calls on Groq free tier, no re-embedding)

**B1. Backfill company + role** — Python script `worker/scripts/backfill_metadata.py`
- Query all nuggets with `company IS NULL` or `role IS NULL`
- Batch 10 nuggets per LLM call with user's known company list as context
- LLM assigns company + role from nugget_text + answer content
- Normalize company names: build `COMPANY_ALIASES` map (`"Amex" → "American Express"`)
- Apply normalization to ALL rows (including already-populated ones)
- Tag: `company_backfilled`, `role_backfilled`

**B2. Backfill event_date** — same script
- LLM infers approximate dates from context + known company tenure
- Convert to YYYY-MM-DD format before DB write
- Tag: `event_date_backfilled`, `event_date_approx`

**B3. Fix section_type NULLs** — same script
- 34 nuggets need Layer A classification
- Tag: `section_type_backfilled`

**B4. Add company alias resolution to retrieval**
- File: `worker/app/tools/hybrid_retrieval.py` — new `_normalize_company()` function
- Apply in `_bm25_query()`: expand `eq("company", co)` to include aliases
- Apply in orchestrator Phase 2.5 company matching (`orchestrator.py:608`)

---

### Phase C: Answer Enrichment + Re-embedding (LLM + Jina API cost)

**C1. Enrich answers to be self-contained** — `worker/scripts/backfill_answers.py`
- DEPENDS ON: Phase B (needs company/role/date populated first)
- For each answer missing company name as substring:
  - LLM rewrites: "At {company} as {role} ({year}), {achievement with metrics}"
  - Validation: assert company in new_answer, assert all numbers preserved
  - Fallback: mechanical prepend if LLM validation fails
- Store `answer_original` hash in tag for audit
- Tag: `answer_enriched`

**C2. Re-embed enriched answers** — `worker/scripts/backfill_reembed.py`
- Select rows tagged `answer_enriched`
- Clear embedding → call `embed_nuggets()`
- ~225 rows / 5 per batch = 45 Jina calls (~90 seconds)

**C3. Verify retrieval improvement**
- Run hybrid_retrieve for "American Express", "Sprinklr", "Walmart"
- Compare hit count before vs after
- Spot-check that Phase 4A context now contains company/role/date in every nugget

---

### Phase D: Low-Priority Backfill

**D1. Re-score resume_relevance** — review 42 nuggets below 0.5 threshold
**D2. Backfill people field** — extract stakeholder names from nugget_text

---

### Phase E: Prevention (future extraction quality)

**E1. Strengthen extraction prompt** — `worker/app/tools/nugget_extractor.py:31-68`
- Add 2-3 few-shot examples (correct vs incorrect extraction)
- Add self-check instruction: "After generating, verify every work_experience has company + role non-null"
- Strengthen answer format: "Begin with 'At {company} as {role} ({year}), ...'"

**E2. Mirror prompt changes in frontend** — `website/src/lib/nugget-extraction-prompt.ts`

**E3. Add post-extraction `_validate_nugget()` function**
- File: `worker/app/tools/nugget_extractor.py` (before DB insert)
- Check: work_experience has company/role, answer contains company substring, Layer A has section_type
- Tag violations but don't block insert

**E4. Strengthen Zod schema in ingest API**
- File: `website/src/app/api/nuggets/ingest/route.ts`
- Add `.refine()`: work_experience requires company, Layer A requires section_type
- Add event_date coercion ("YYYY" → "YYYY-01-01")

---

## Critical Files

| File | Changes |
|------|---------|
| `worker/app/tools/hybrid_retrieval.py` | NULL handling (A3), duplicate exclusion (A4), BM25 fallback (A5), company aliases (B4) |
| `worker/app/tools/nugget_extractor.py` | event_date coercion (A6), prompt improvement (E1), validation (E3) |
| `worker/app/pipeline/orchestrator.py` | Company normalization in Phase 2.5 (B4) |
| `website/src/lib/nugget-extraction-prompt.ts` | Prompt sync (E2) |
| `website/src/app/api/nuggets/ingest/route.ts` | Zod refinements (E4) |
| `worker/scripts/backfill_metadata.py` | NEW — company/role/date backfill (B1-B3) |
| `worker/scripts/backfill_answers.py` | NEW — answer enrichment (C1) |
| `worker/scripts/backfill_reembed.py` | NEW — targeted re-embedding (C2) |
| New migration `006_nugget_text_fts.sql` | GIN index on nugget_text (A5) |

## Verification

1. **After Phase A**: Run `SELECT count(*) FROM career_nuggets WHERE 'duplicate_archived' = ANY(tags)` — expect 20
2. **After Phase B**: Run `SELECT count(*) FROM career_nuggets WHERE company IS NULL AND section_type = 'work_experience'` — expect 0
3. **After Phase C**: Run BM25 search for "American Express" on answer column — expect 80+ hits (vs current 32)
4. **After Phase C**: Generate a test resume targeting AmEx — verify Phase 4A context contains company+role+date in every nugget header
5. **End-to-end**: Dashboard at `/dashboard/nuggets` shows zero "unembedded" nuggets, company filter works, date filter works
