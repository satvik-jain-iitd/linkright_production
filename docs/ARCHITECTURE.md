# LinkRight — Architecture Reference

> Authorized document. Last updated: 2026-05-08. Merges: ARCHITECTURE-DECISIONS.md, MODULE-REFERENCE.md, CODE-PATTERNS.md, BUILD-LEARNINGS.md, LINKRIGHT_QUALITY_REFERENCE.md.

---

## System Map (Current — May 2026)

```
User
 │
 ├── linkright CLI (PyPI package, Python)
 │   ├── context/cli/linkright/src/linkright/
 │   ├── ~/.linkright/ (profile, runs, config, API keys)
 │   └── Groq / Cerebras / Z.ai / SambaNova / Cloudflare / Gemini (free cascade)
 │
 ├── Website (sync.linkright.in, Next.js on Vercel)
 │   ├── repo/website/src/
 │   └── Supabase (user data + PII)
 │
 ├── Worker (Python, job processing)
 │   ├── repo/worker/
 │   └── Oracle Postgres (job/company data)
 │
 └── Oracle VPS (80.225.198.184)
     ├── Postgres — job_discoveries, companies, analytics
     ├── Ollama — gemma3:1b (production proxy enforces this model)
     └── lr-backend (FastAPI port 8000)
```

**DB split rule (locked):** Job/company/analytics data → Oracle Postgres. User PII → Supabase. Never mix.

---

## CLI Architecture

### Pipeline — 16 Steps

| Step | File | What |
|------|------|------|
| 01 | `jd_keyphrase.py` | JD keyword extraction |
| 02 | `pdf_parse.py` / `md_parse.py` | Resume + JD parsing |
| 03 | `orchestrator.py` | Signal extraction via nugget pipeline |
| 04–06 | `jobsearch/evaluator.py` | Requirement matching + gap analysis |
| 07 | `pipeline.py` | Strategy selection |
| 07b | `pipeline.py` | User outline review checkpoint (human-in-the-loop) |
| 08–09 | `tools/score_bullets.py` | BRS bullet scoring + tier assignment |
| 10 | `agents/bullet_writer.py` | XYZ bullet generation + width-fit loop |
| 11 | `tools/suggest_synonyms.py` | Width optimization via synonym substitution |
| 12 | `tools/measure_width.py` | Pixel-precise width validation |
| 13 | `assemble_html.py` | HTML template injection |
| 14 | `tools/validate_page_fit.py` | A4 page-fit check |
| 15 | Playwright | PDF render |
| 16 | `agents/quality_judge.py` | 16-dimension scorecard |

### Key Source Paths
- Entry point: `src/linkright/cli.py` + `src/linkright/pipeline.py`
- LLM calls: `src/linkright/llm/direct.py` (3-layer config: built-in + ~/.linkright/agents.yaml + env vars)
- Schemas: `src/linkright/schemas/` (CareerSignals, JDAnalysis, QualityReport, WrittenBullet)
- Tools: `src/linkright/tools/` (measure_width, suggest_synonyms, score_bullets, track_verbs, validate_page_fit)

### LLM Provider Cascade (TIER_POLICY — small-first, free)

| Quality Class | Steps | Primary | Fallback |
|---------------|-------|---------|---------|
| Class A: Extraction | step_01, step_06 | groq_8b | cerebras_8b → cloudflare_3b |
| Class B: Surgical edit | step_09 summary | groq_8b | cerebras_8b |
| Class C: Generation | step_10 bullets | cerebras_8b | z_ai_glm | sambanove_70b |
| Class D: Judgment | step_07, step_10 eval | sambanove_70b | gemini_flash |

24 API keys total (4 per provider). Per-provider rotation via `_collect_keys()`. Temperature=0 for extraction, 0.3–0.5 for generation.

---

## Quality Gates (Exact Implementation)

### Quality Judge — 6 Checks

| Check | Weight | What | Pass Condition |
|-------|--------|------|---------------|
| Keyword Coverage | 30% | % P0/P1 JD keywords in bullets | Higher = better |
| Width Fill Avg + Min | 25% | Average fill % across bullets | 90–100% per bullet = PASS |
| Verb Deduplication | 15% | Repeated action verbs across bullets | No duplicates = 100pts |
| Page Fit | 15% | All content fits one A4 page | fits_one_page = True |
| Color Contrast | 10% | Brand color WCAG AA on white | ratio ≥ 4.5:1 |
| ATS Compliance | 5% | No `<table>` or `<img>` in bullets | No issues = 100pts |

**Grade thresholds:** ≥90 = A, ≥75 = B, ≥60 = C, ≥40 = D, <40 = F.

### BRS Scoring — 5 Factors

| Factor | Weight | How Scored |
|--------|--------|-----------|
| Keyword Overlap | 35% | matched_keywords / total_p0_p1_keywords (capped 1.0) |
| Metric Magnitude | 25% | 1.0 if $-amount or %, 0.7 if any number, 0.3 if qualitative |
| Recency | 20% | entry_index 0→1.0, 1→0.8, 2→0.6, 3+→0.4 |
| Leadership | 10% | strong verbs→1.0, collaborative→0.5, none→0.0 |
| Uniqueness | 10% | no overlap→1.0, partial→0.5, all dupes→0.0 |

**Tier assignment:** BRS ≥0.7 = Tier 1 (must-include), 0.4–0.7 = Tier 2, <0.4 = Tier 3.

### Width Fitting — Retry Loop

```
Initial write → measure_width() →
  if PASS (90–100%): done
  if TOO_SHORT: suggest_synonyms(expand) → revise → measure again
  if OVERFLOW: suggest_synonyms(trim) → revise → measure again
  max 3 retries, accept final status after
```

Width rule: target = 95% of line budget (safety buffer). Status: <90% = TOO_SHORT, 90–100% = PASS, >100% = OVERFLOW.

### Page Fit
- A4 usable height = 271.6mm
- Section heights computed via SectionSpec per-section breakdown
- Recommendation: "fits" / "tight" / "overflow"

### WCAG Contrast
- Body text (9.5pt Roboto) = normal text → requires 4.5:1
- Validate: `validate_contrast(foreground_hex, background_hex)`

---

## Key Pydantic Schemas

### CareerSignals (career_signals.yaml source of truth)
```python
class Signal:
    id: str                    # "sig-001"
    company: str
    role: str
    signal_type: str           # "job"|"internship"|"freelance"|"project"
    achievements: list[Achievement]
    context: SignalContext      # team_size, scope, budget, tech_stack

class CareerSignals:
    metadata: Metadata         # user, email, phone, linkedin_url
    static: StaticSection      # skills, education, voluntary, interests
    signals: list[Signal]
```

### JDAnalysis
```python
class JDAnalysis:
    company_name: str
    role_title: str
    career_level: str          # "fresher"|"entry"|"mid"|"senior"|"executive"
    strategy: str              # "METRIC_BOMBARDMENT"|"SKILL_MATCHING"|"LEADERSHIP_NARRATIVE"|"TRANSFORMATION_STORY"|"BALANCED"
    keywords: list[JDKeyword]  # priority: "P0"|"P1"|"P2"
    brand_colors: BrandColors  # primary, secondary, tertiary, quaternary
    requirements_p0/p1/p2: list[str]
```

### QualityReport
```python
class QualityReport:
    overall_grade: str         # "A"|"B"|"C"|"D"|"F"
    keyword_coverage: float    # % of P0/P1 keywords in bullets
    width_fill_avg: float
    width_fill_min: float
    verb_duplicates: list[str]
    page_fits: bool
    contrast_passes: bool
    ats_issues: list[str]
    suggestions: list[str]
```

### WrittenBullet
```python
class WrittenBullet:
    signal_id: str             # links to career_signals.yaml
    html_text: str             # final HTML with <b> tags
    plain_text: str
    fill_percentage: float     # 0–100+
    width_status: str          # "PASS"|"TOO_SHORT"|"OVERFLOW"
    action_verb: str           # for dedup tracking
```

---

## Website Architecture

- **Framework:** Next.js (App Router) on Vercel
- **Auth:** Supabase auth
- **DB:** Supabase (user PII) + Oracle Postgres (jobs/companies)
- **Key routes:** `/auth`, `/onboarding`, `/dashboard`, `/resume`, `/customize`, `/extension`, `/api/*`
- **API routes:** All under `src/app/api/` — rate-limited via `rateLimit()` (73 connections — god node)
- **Critical dependency:** `createClient()` — 119 edges, called by every API route. Single point of failure if Supabase auth breaks.
- **Brand colors:** `fetchFromBrandfetch()` → Oracle Postgres cache → `persistBrandColors()` → resume theming

---

## Key Architecture Decisions (Locked)

| Decision | Chosen | Why |
|----------|--------|-----|
| Vector DB | MongoDB $vectorSearch | Already running, docs+vectors in one DB, zero cost |
| Embedding (career signals) | Jina AI v3 1024d | Free 1M tokens, best quality for life/career content |
| Embedding (fastembed CLI) | BAAI/bge-small-en-v1.5 384d | Local, fast, zero cost per resume |
| Chunking | Q&A pair FAQ preprocessor | +10% P@1 over fixed chunking |
| LLM runtime | Direct mode CLI only | Claude Max = zero subscription quota |
| Server | Oracle Free Tier | 24GB RAM, 200GB disk, forever free |
| Job data | Oracle Postgres | 200GB VPS, separate from user PII |
| User data | Supabase | Hosted, handles auth |
| Width calc | Roboto hmtx font metrics | Character count is wrong (W ≠ i in width) |

---

## State Logging (Crash Safety)

Pipeline saves JSON after every step to `.linkright/state/`:
```
1_inputs_loaded.json → 2_jd_analysis.json → 3_scored_bullets.json →
4_written_bullets.json → 5_assembled.json → 6_quality_report.json
```
Rule: never buffer everything in memory — crash at step N means steps 1..N-1 are safe.

---

## Code Standards

1. Rich JSDoc/docstring header on every file
2. Function purpose doc (WHAT + WHY, not HOW)
3. Descriptive filenames (score_bullets.py, not utils.py)
4. One concern per file
5. Comments = WHAT not HOW
6. Constants need context in comments
7. No re-export pollution in `__init__.py`

---

## Old Architecture (Historical — pre-2026-04-15)

The original LinkRight used Oracle VPS MongoDB + LifeOS module + n8n orchestration. Key components that were abandoned:
- **ChromaDB:** Docker persistence issues → replaced by MongoDB $vectorSearch
- **LifeOS module:** Separate diary/vector system → merged into career nuggets pipeline
- **Flex/Scout/AutoFlow modules:** Deferred to v2
- **n8n webhooks:** Overkill for current scale
- **AWS EC2:** Free tier expired April 12, 2026 → fully on Oracle
