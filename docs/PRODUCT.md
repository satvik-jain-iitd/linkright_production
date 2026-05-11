# LinkRight — Product Reference

> Authorized document. Last updated: 2026-05-12. Merges: PRODUCT-VISION.md, V01-REQUIREMENTS.md, linkright-cli-milestone-2026-05-02.md.

---

## What LinkRight Is

LinkRight is an AI-powered career OS that turns raw life experience into tailored job application artifacts. Core product: a CLI tool that takes your resume + a job description and produces a pixel-perfect, ATS-optimized single-page PDF in ~2 minutes for $0.

**Positioning:** "ChatGPT generates content. LinkRight engineers signal."

---

## Current State — May 2026

### CLI (v0.8.0, live on PyPI)

**Sprint history:** Sprint 1 (12 bug fixes + UI, v0.5.x) → Sprint 2 (token foundations, v0.6.0) → Sprint 3 (subliminal + truth engine, v0.7.0) → Sprint 4 (polish + UX, v0.8.0)

- Install: `pip install 'linkright[full]'`
- Quality score milestone: 76.7 (C+) → 97.2 (A) — achieved 2026-05-02
- Wall time per resume: ~2 minutes (121 seconds)
- API calls per resume: 5 (profile cache saves 8–10 calls)
- Tokens per resume: ~19,488 (baseline); target <13,000 via Sprint 5 caching
- Cost per resume: **$0.00** — Groq + Cerebras + Z.ai + SambaNova free tiers, 24 keys, 421,840 RPD capacity
- Daily theoretical capacity: 84,368 resumes/day; 24-resume daily usage = 0.03% of capacity

**Shipped in Sprints 1-4 (v0.5.x → v0.8.0):**
- Experience years ceiling-rounding + fresher-drop in summary (S1.1)
- Fabrication guard tuned — real action verbs never stripped (S1.2)
- Human-friendly spinner labels, no internal step names visible (S1.3)
- Groq setup --check false-negative fixed (S1.4)
- GenAI/LLM/RAG acronym expansion fixed — no "Gen-artificial intelligence" (S1.5)
- Trailing punctuation residues removed from all bullets (S1.6)
- CLI terminal UI: Claude Code-style patterns + LinkRight palette (#4285F4/#EA4335/#34A853) (S1.8)
- Location truth-engine guard — no LLM-hallucinated locations (S1.9)
- LinkedIn/Portfolio render as clickable hyperlinks, not raw URLs (S1.10)
- Acronym expansion bank: 344 entries across 12 domains (S2.1)
- Industry-domain verb prefix maps for deterministic verb substitution (S2.2)
- Verb taxonomy: 720 entries, impact-category × industry 2D matrix (S2.3)
- Signal-weighting matrix: 13 × 5 career-level multipliers in BRS scoring (S3.1)
- JD requirement clustering: cosine-similarity anti-stuffing in step_11 (S3.2)
- Truth Engine Layer 1: personal-details verification at pipeline start (S3.3)
- Markdown profile ingestion + privacy gate (S3.4)
- Peer-vs-applicant language bank: seniority-tone calibration in step_10 (S4.1)
- Career-level vocab profile: authority/credibility/energy verbs per level (S4.2)
- Metric-magnitude consistency enforcement: mixed-tier penalty in BRS (S4.3)
- Success box shows JD coverage % + width hit-rate after every tailor run (S4.4)
- Success box PDF path no longer wraps mid-filename (S4.5)

### Website (sync.linkright.in, live on Vercel)
- Next.js app: auth, onboarding, dashboard, resume builder, Oracle/job-search features
- Website mirrors CLI behavior; CLI is source of truth for all quality rules

### Pipeline — 16 steps
| Phase | Steps | What Happens |
|-------|-------|-------------|
| Profile (one-time) | 01–03 | PDF → 21 career nuggets + 384-dim embeddings |
| JD Analysis | 04–07b | JD parsing → keywords → strategy → user approves outline |
| Bullet Generation | 08–12 | BRS scoring → XYZ bullet write → width fit → metric fill |
| Assembly | 13–15 | HTML assemble → page-fit validate → Playwright PDF render |
| QA | 16 | 16-dimension quality scorecard |

---

## 4 Pillars (Full Vision)

| Pillar | What | Status |
|--------|------|--------|
| **1. Resume** | JD-tailored resume, cover letter, quality scorecard | **v0.8.0 SHIPPED** |
| **2. Job Search** | Seed + expand job discovery, dual-read Oracle+Supabase | In development |
| **3. Interview** | Story bank (STAR answers from career nuggets) | Scoped to Story Bank only; mock interview = v2 |
| **4. Content** | LinkedIn content pipeline from career signals | Deferred post-v1 |

**v1 scope locked (2026-05-03):** Story Bank + QA plan + cleanup + resume/CL polish → then public GitHub release.

---

## Target User

**Primary: Title-Mismatch PM**
- 4–8 years experience, enterprise brand (AmEx / Sprinklr tier)
- Performs PM work without PM title
- Targeting FAANG-tier / global SaaS PM at 40%+ compensation increase
- Current pain: <20 manual apps/month, 45+ min per application, <1% shortlist rate
- Desired: <15 min per tailored resume, 5%+ interview conversion rate

**Secondary segments (5 total):**
1. Frustrated Active Seeker (25–35, 3–7 YOE) — 40% of market, WTP $25–50/mo
2. Ambitious Graduate (22–25, 0–2 YOE) — 25%, WTP $15–25/mo
3. Career Switcher (28–40, 5–12 YOE) — 20%, WTP $30–60/mo
4. Passive Seeker (30–45, 8–15 YOE) — 10%, WTP $20–40/mo
5. Executive (40–55, 15+ YOE) — 5%, WTP $100–300/mo

---

## North Star Metrics

| Metric | Target |
|--------|--------|
| Interview Conversion Rate | ≥5% (interviews / applications) |
| Time per tailored application | <15 min (from 45+ min) |
| JD Alignment Score uplift | ≥20% |
| Monthly infrastructure cost | Rs.0 (Oracle Free Tier) |

**Revenue targets:** Month 3: $2K MRR → Month 6: $10K → Month 12: $50K MRR.

---

## Business Model

| Tier | US | India |
|------|----|-------|
| Free | $0 (5 apps/mo) | $0 |
| Pro | $29/mo | Rs 999/mo |
| Premium | $99/mo | Rs 2,999/mo |

Infrastructure cost trajectory:
- Now (1 user): Rs.0/month — Oracle Free Tier forever
- 1K–10K users: $200–500/mo (MongoDB Atlas Flex + compute)
- 100K+ users: $10K+/mo

---

## What Works (Empirically Validated)

1. **Q&A pair embedding beats raw chunking.** FAQ P@1 50% vs Chunk P@1 40% (+10%).
2. **Tailored resumes produce 2× interview rates.** ~6 interviews per 100 tailored vs <3 generic (Huntr 2025, 1.39M applications).
3. **Programmatic quality gates work.** LLM writes → script validates → failure feeds back → 3 failures → human. Separates creativity from standards.
4. **Small-first LLM cascade at $0.** Groq/Cerebras 8B models handle 90% of tasks; SambaNova 70B for judgment calls. Total cost = $0.
5. **Hash-based change detection saves 99% API calls.** SHA256 per file → only re-embeds changed content.
6. **Width-first bullet engineering.** Pixel-precise measurement via Roboto hmtx font metrics. Never hardcode character counts.
7. **Hybrid search (vector + keyword) is essential.** Vector alone: 60%, combined: 75–85%.

## What Doesn't Work (Anti-Patterns)

1. **Hardcoded character limits.** W is 3.59× wider than i in Roboto. Must measure pixel width.
2. **Full-batch embedding without partial save.** 950 chunks embedded → crash → zero saved. Always persist after each batch of 20.
3. **Docker ChromaDB.** Overhead, persistence issues. Switched to MongoDB $vectorSearch.
4. **Self-reported quality scores.** Kali Score was self-reported, not computed. Gates must be programmatic.
5. **LLMs fabricating metrics.** Gemini hallucinated numbers not in career_signals.yaml. Always cross-check metrics against source data.
6. **Frontend-first development.** Hard-won lesson: CLI first → MCP second → UI third.
7. **Hostage pricing (build free, pay to download).** Resume.io / Zety pattern. Generates toxic brand equity.
8. **MCP server with zero auth.** Destructive operations must require confirmation. Collection drops = BLOCKED.

---

## 12 Core Rules

1. One module until A-grade before moving on
2. Three agents maximum per pipeline
3. CLI-first, no frontend until CLI is solid
4. Zero Docker for end users
5. Direct mode is canonical (not agent mode) — saves quota
6. Width calculation from day one (Roboto hmtx, not char counts)
7. Crash-safe pipelines (save after every batch)
8. One repo, one copy (<500 files)
9. Security hygiene from day zero (pre-commit hooks, no keys in git)
10. Beads for tracking, not theater (<20 issues/day)
11. Kill the glue, test the boundaries (integration tests at schema handoffs)
12. Never claim "live/integrated" without testing it

---

## Market Context

- **TAM:** ~$19.7B globally (Resume SaaS + Coaching + Premium Networking)
- **India:** $800M, 5.8M tech workforce, net hiring 126K/year FY2025
- **AI Applicant Tsunami:** LinkedIn saw 45% YoY surge in application volumes 2025
- **Competitive gap:** Market saturated with tools that help users apply; severely underserved in tools that help users connect and navigate.
