# Sprint C Phase 1 — Implementation Spec (Naukri userscript MVP)

> **Date**: 2026-05-03
> **Parent spec**: `specs/sprint-c-passive-capture-architecture-2026-05-03.md`
> **Phase 1 goal**: 1-week empirical capture validation on Naukri using Tampermonkey userscript + minimal backend endpoint
> **Status**: AWAITING SATVIK SIGN-OFF before writing code

---

## Federation pattern (per locked DB-split rule — CORRECTED 2026-05-03 evening)

> **Correction note (3rd reaffirmation by Satvik)**: an earlier draft of this spec proposed writing captures to the LEGACY Supabase `job_discoveries` table with the rationale "the rule allows reusing legacy tables for new code paths". Satvik rejected that reading. The corrected rule: **ANY new job-related write path goes to Oracle PG, period — even if a Supabase table already exists for it.** This spec now creates a NEW `job_discoveries` table on Oracle PG via migration 006.

```
USER's Chrome (Naukri TopTier session)
    ↓ Tampermonkey userscript intercepts XHR/DOM on naukri.com/job-listings/* pages
    ↓ POST /api/captures   (with X-LinkRight-Capture-Key header for auth)
        ↓
LinkRight worker (FastAPI on Render)
    ↓ Step 1: validate Pydantic payload
    ↓ Step 2: Oracle PG — lookup or create `companies` row
    │           (if found by lower(name) match → use existing canonical_id;
    │            if not → INSERT with confidence='medium', source=['passive_capture_naukri'])
    ↓ Step 3: Oracle PG — upsert NEW `job_discoveries` row (migration 006)
    │           (dedup by job_url; source_type='capture_naukri';
    │            company_canonical_id FK to companies)
    ↓ Step 4: Oracle PG — feedback to slug_discovery_cache
    │           (if Naukri URL reveals identifiable ATS pattern → cache it)
    ↓ Return { ok, job_id, dedup_status: 'new' | 'updated' | 'skipped' }
```

**Why Oracle PG (not Supabase legacy reuse)**:
- LOCKED architectural rule: NEW job-related write paths target Oracle PG, period
- Future Stage-5 migration moves the legacy Supabase `job_discoveries` to Oracle PG too — at which point the legacy table dies. New writes pre-emptively target the eventual location.
- Pillar 2's `linkright jobsearch find` currently reads from Supabase legacy. Phase 1 of Sprint C does NOT update Pillar 2's read path — Phase 1 verifies captures via SQL queries against Oracle PG directly. Pillar 2 dual-read (Supabase + Oracle) is Phase 2 work OR can be folded into the Stage-5 migration sprint.

---

## API contract

### Endpoint
`POST /api/captures`

### Headers
- `Content-Type: application/json`
- `X-LinkRight-Capture-Key: <env-set tenant key>` — for Phase 1 = single key for Satvik's tenant; rotated when needed

### Request body (Pydantic model `CaptureIn`)
```python
class CaptureIn(BaseModel):
    source: Literal["naukri", "linkedin", "indeed", "wellfound"]  # Phase 1 = naukri only
    job_url:        HttpUrl                  # canonical URL — primary dedup key
    external_id:    Optional[str]            # platform's own job id (Naukri jid, LinkedIn id)
    title:          str
    company_name:   str
    company_website: Optional[HttpUrl]       # if Naukri page exposes it (often does)
    location:       Optional[str]
    salary_text:    Optional[str]            # raw "8-12 LPA" string — only if PUBLIC on the page
    jd_text:        Optional[str]            # full JD body — capped at 50KB
    posted_at:      Optional[datetime]
    captured_at:    datetime                 # client clock — server may override with NOW()
    raw_payload:    Optional[dict]           # original capture for debugging (capped at 100KB)

    @field_validator("salary_text", "jd_text")
    def length_cap(cls, v):
        # privacy + DB-bloat guard: hard caps
        return v[:MAX_LEN] if v else v
```

### Response (Pydantic model `CaptureOut`)
```python
class CaptureOut(BaseModel):
    ok: bool
    job_id: Optional[str]                    # Supabase row id
    canonical_id: Optional[str]              # Oracle PG companies row id
    dedup_status: Literal["new", "updated", "skipped"]
    company_status: Literal["matched_existing", "created_new"]
    notes: Optional[str]                     # human-readable hint for userscript console
```

### Error semantics
- `400 Bad Request` — Pydantic validation failed
- `401 Unauthorized` — missing or wrong `X-LinkRight-Capture-Key`
- `403 Forbidden` — payload domain blocked by privacy filter (caller bug — should never reach server)
- `429 Too Many Requests` — rate limit hit (1 request / sec / tenant for Phase 1)
- `500 Internal Server Error` — DB write failed; userscript retries with exponential backoff up to 3x

---

## Privacy filter (server-side — defense in depth even though userscript filters too)

Reject capture if:
- `job_url` host not in allowlist (`naukri.com` for Phase 1)
- `job_url` path matches blocklist (`/messages`, `/notifications`, `/connections`, `/inbox`, `/profile`, `/myaccount`, `/m/profile`)
- `jd_text` or `raw_payload` contains markers of private content (e.g., "Inbox:", "From:", "To recipient:")
- `salary_text` matches a personal-comp pattern (e.g., contains "Your offer:" or "Your CTC:") rather than a public range

Privacy violations log to Supabase `capture_audit` table (PII-bound) so Satvik can review what was rejected and why. NOT silently dropped.

---

## Auth model for Phase 1

Single `X-LinkRight-Capture-Key` env var on the worker, set to a Satvik-only secret. The userscript embeds this key in the Tampermonkey config menu (NOT hardcoded in the .user.js file).

When we open Phase 1 to beta users (Phase 2+), this becomes per-tenant via Supabase auth.users → tenant_id mapping.

---

## DB writes

### Oracle PG `companies` (lookup or create)

```sql
-- Step 2a: lookup existing
SELECT canonical_id FROM companies WHERE lower(name) = lower($1) LIMIT 1;

-- Step 2b: if not found, INSERT
INSERT INTO companies (canonical_id, name, website, source, confidence, hiring_active, ingested_at)
VALUES (
  encode(sha256(coalesce($website, $name)::bytea), 'hex')::char(40),
  $name,
  $website,
  ARRAY['passive_capture_naukri'],
  'medium',
  TRUE,
  NOW()
)
ON CONFLICT (canonical_id) DO UPDATE SET
  source = array_append(companies.source, 'passive_capture_naukri'),
  hiring_active = TRUE
  -- DON'T overwrite name/website if already known (admin-curated wins)
RETURNING canonical_id;
```

### Oracle PG `job_discoveries` (NEW table via migration 006 — upsert by job_url)

Schema (migration 006 — `worker/db/oracle_migrations/006_job_discoveries.sql`):
```sql
CREATE TABLE job_discoveries (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_url              text NOT NULL UNIQUE,
  external_job_id      text,
  title                text NOT NULL,
  company_name         text,
  company_canonical_id text REFERENCES companies(canonical_id) ON DELETE SET NULL,
  location             text,
  salary_text          text,
  jd_text              text,
  posted_at            timestamptz,
  source_type          text NOT NULL,          -- 'capture_naukri', 'capture_linkedin', etc.
  status               text NOT NULL DEFAULT 'new',
  liveness_status      text NOT NULL DEFAULT 'active',
  enrichment_status    text NOT NULL DEFAULT 'pending',
  raw_payload          jsonb,
  captured_at          timestamptz NOT NULL DEFAULT NOW(),
  updated_at           timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_jd_company    ON job_discoveries(company_canonical_id);
CREATE INDEX idx_jd_source     ON job_discoveries(source_type);
CREATE INDEX idx_jd_captured   ON job_discoveries(captured_at DESC);
CREATE INDEX idx_jd_active     ON job_discoveries(status, liveness_status)
                                 WHERE status = 'new' AND liveness_status = 'active';
```

Schema-compatible with the legacy Supabase `job_discoveries` for the future Stage-5 migration (column names match). The legacy Supabase table continues serving Pillar 2 reads; new captures live in Oracle PG. Stage-5 migration eventually consolidates.

---

## Open questions (need Satvik decision before code)

1. **Salary capture**: Naukri job pages often show salary range ("8-12 LPA"). Is that OK to capture, or do you want salary fully blocked from captures (only inferred from internal heuristics)? My default = capture if PUBLIC on the page.

2. ~~**Company FK column on Supabase `job_discoveries`**~~ — **OBSOLETE** after the Oracle-PG-only correction (2026-05-03). New Oracle `job_discoveries` table has its own `company_canonical_id` column with proper FK to `companies(canonical_id)`. No Supabase schema change.

3. **`X-LinkRight-Capture-Key` storage**: where does this secret live?
   - (a) Render env var (worker reads at startup)
   - (b) Vercel env var (proxied through Vercel function to worker)
   - (c) Both (different keys for direct-to-worker vs Vercel-proxied)
   - My default = (a) for Phase 1; Vercel proxy added in Phase 2 if needed for CORS reasons.

4. **Userscript hosting**: where do you install it from?
   - (a) GitHub Gist URL (Tampermonkey auto-updates from raw URL)
   - (b) Inline-paste from a code block
   - (c) Repo file (`extension/naukri-capture.user.js`) with raw GitHub URL
   - My default = (c) — versioned in this repo, raw URL for Tampermonkey auto-update.

5. **Capture rate limiting**: 1 req/sec/tenant for Phase 1. OK or want different?

---

## Phase 1 deliverables (estimated effort)

| Item | Files | Effort |
|---|---|---|
| 1. New worker endpoint `POST /api/captures` | `worker/app/api_captures.py` (NEW) + register in `worker/app/main.py` | ~2 hrs |
| 2. Federation logic (Oracle companies + Supabase jobs) | `worker/app/captures/persist.py` (NEW) | ~2 hrs |
| 3. Pydantic models | `worker/app/captures/models.py` (NEW) | ~30 min |
| 4. Privacy filter | `worker/app/captures/privacy.py` (NEW) | ~30 min |
| 5. Oracle PG migration: NEW `job_discoveries` table | `worker/db/oracle_migrations/006_job_discoveries.sql` | ~30 min |
| 6. Tests (unit + 1 integration) | `worker/tests/captures/test_*.py` | ~1 hr |
| 7. Naukri userscript MVP | `extension/naukri-capture.user.js` (NEW) | ~1.5 hr |
| 8. Install instructions for Satvik | `extension/INSTALL.md` (NEW) | ~15 min |
| **Total** | 8 files | **~7-8 hours** |

---

## What I will do AFTER Satvik signs off

1. Answer the 5 open questions inline in this spec
2. Set up Render env var for `X-LinkRight-Capture-Key` (need Satvik to add to Render dashboard OR I can do via Render CLI if creds available)
3. Code in order: Pydantic → privacy filter → persist → endpoint → tests → migration → userscript → install
4. Commit per logical chunk; one PR for the full Phase 1
5. Dispatch AR for sign-off
6. Hand off install instructions to Satvik

---

## Anti-scope (do NOT do in Phase 1)

- ❌ LinkedIn capture (Phase 2)
- ❌ User behavioral signals (clicks, dwell) — Phase 2
- ❌ Cross-site dedup (same job on Naukri + LinkedIn) — Phase 2
- ❌ Pretty UI for capture inspector — Phase 3 (Chrome extension)
- ❌ Auto-update Naukri parser when their HTML changes — manual fixes for Phase 1
- ❌ Move job_discoveries from Supabase to Oracle PG — separate migration sprint
