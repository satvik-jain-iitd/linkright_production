# LinkRight — Roadmap & Backlog

> Authorized document. Last updated: 2026-05-12. Merges: linkright-pillar2-jobsearch.md, sprint-c-passive-capture.md, wave-8-extension-spec.md, website-improvements-deferred.md, future_roadmap.md, context/ideas/.

---

## Current Sprint — Sprint 5 (v0.9.x, week of 2026-06-08)

**Goal:** Local-model quality + pipeline optimization (7 items). See `# LinkRight PRD.md §6 Sprint 5` for full specs.

| ID | Item | Priority | Status |
|----|------|----------|--------|
| S5.1 | Embedding-based JD-bullet alignment (nomic-embed-text, step_11) | P1 | 🔄 Planned |
| S5.2 | Request-level output caching (>25% cache hit rate target) | P1 | 🔄 Planned |
| S5.3 | JD keyword contamination prompt fix | P1 | 🔄 Planned |
| S5.4 | Career level classification → pure deterministic (remove LLM call) | P2 | 🔄 Planned |
| S5.5 | Progressive validation gate (early regen on BRS-weak bullets) | P1 | 🔄 Planned |
| S5.6 | Cross-bullet verb coherence enforcer (Oracle local gemma3:1b) | P1 | 🔄 Planned |
| S5.7 | Fine-tuned fabrication guard (asymmetric loss, gemma3:1b) — data collection running since Sprint 1 | P0 | 🔄 Data collection in progress |

**⚠️ S5.7 lead time:** Requires 3 weeks including data collection. `step_10b` instrumentation collecting `(bullet, source_excerpt, guard_decision)` triplets passively since Sprint 1.

---

## Completed Sprints (v0.5.x → v0.8.0)

**Goal:** Public GitHub release of LinkRight v1.

| Sprint | Version | Items | Status |
|--------|---------|-------|--------|
| Sprint 1 — Bug-fix + UI foundation | v0.5.12–v0.5.24 | 12 items: S1.1–S1.12 | ✅ Done |
| Sprint 2 — Token-cost foundations | v0.6.0 | 3 items: S2.1 acronym bank, S2.2 verb maps, S2.3 verb taxonomy | ✅ Done |
| Sprint 3 — Subliminal + truth + long-doc | v0.7.0 | 4 items: S3.1 signal weights, S3.2 JD clustering, S3.3 truth engine L1, S3.4 markdown ingest | ✅ Done |
| Sprint 4 — Polish + UX | v0.8.0 | 5 items: S4.1 peer lang, S4.2 career vocab, S4.3 metric magnitude, S4.4 success metrics, S4.5 path wrap | ✅ Done |

**v1 Ship Checklist (original, now updated):**

| Item | Status |
|------|--------|
| Resume tailor pipeline (16 steps, A grade) | ✅ Done |
| Cover letter (`linkright cl`) | ✅ Done |
| CLI polish (19-item UX backlog — Sprints 1-4) | ✅ Done (v0.8.0) |
| v0.4.0 fix plan (22 issues) | ✅ Done (Sprint 1) |
| Pillar 2 job search (seed + expand) | 🔄 In progress |
| Story Bank — Pillar 3 | 🔄 Scoped |
| Manual QA plan v1 pass | 🔄 Pending |

**Scope locked (2026-05-03):** v1 = Story Bank + QA + CLI polish. Mock Interview + Negotiation = v2.

---

## Pillar 2 — Job Search (In Development)

**Problem:** Resume tool is great, but user still has to manually find jobs to apply to.

**4 sub-modules (sequential build):**

### P2.1 — Seed (Structured Intake)
- User specifies: target roles, companies, location, YOE, compensation floor
- Seeds a `job_search_config.yaml` with intent
- Outputs: list of 20–50 target JDs to tailor against

### P2.2 — Expand (Discovery)
- Passive capture from LinkedIn / Naukri / ATS portals via browser extension
- `linkright jobs capture` — saves JD to local store
- Sprint C: passive capture architecture (background capture on portal visits)

### P2.3 — Filter (Scoring)
- Scores each captured job against career profile
- BRS-style scoring: title match + YOE match + domain match + compensation match
- `linkright jobs list --scored` — ranked list of best-fit jobs

### P2.4 — Tailor (Apply)
- `linkright tailor -j <job_id>` — uses Pillar 1 pipeline on stored JD
- Tracks application status: applied → interview → offer / reject
- `linkright jobs track` — application tracker

### Sprint C — Passive Capture Architecture (2026-05-03 spec)
Three passive capture modes:
1. **Network interception** — browser extension intercepts XHR/Fetch to job APIs
2. **DOM snapshots** — periodic capture of job listing pages
3. **WebSocket capture** — for real-time job board updates

Status: architecture spec exists at `specs/sprint-c-passive-capture-architecture-2026-05-03.md`.

---

## Pillar 3 — Interview Prep (Scoped to Story Bank)

**Scope for v1:** Story Bank only.
**Deferred to v2:** Mock Interview, Negotiation Coach.

### Story Bank
- Source: career nuggets (21 nuggets from resume PDF)
- For each nugget: generate STAR-format story (Situation, Task, Action, Result)
- Output: `linkright stories` — prints all STAR stories with JD-alignment tags
- Use case: prep before a Round 1 call in 10 minutes

### v2 (Post-v1 Deferred)
- AI mock interview: conducts practice session, evaluates answers, gives feedback
- JD cheat sheet: rapid-recall card for surprise recruiter calls across multiple active applications
- Negotiation coach: compensation range guidance per role/company/market

---

## Website Improvements (Deferred — Active Backlog)

### Critical Architecture Gap — Job Embeddings
- `job_discoveries` table has NO embedding column (verified 2026-05-01)
- Worker has `nugget_embedder.py` (Jina 768-dim) only for `career_nuggets`
- Match scoring embeds JD text live per query — slow and wasteful at 60K-job scale
- **Fix needed:**
  ```sql
  ALTER TABLE job_discoveries ADD COLUMN embedding vector(384);
  ```
- Add offline embedding job in worker: `fastembed` BAAI/bge-small-en-v1.5 (matches CLI dimension)

### CLI Mirror Items
Per CLAUDE.md rule: "CLI = source of truth. Website mirrors CLI behavior."
- Width calculation in website must use same Roboto hmtx font metrics as CLI
- BRS scoring weights must match exactly (35/25/20/10/10)
- Quality judge checks must match exactly (6 checks, same weights)
- State logging format must match CLI `.linkright/state/` JSON schema

### Other Deferred Website Items
- `linkright jobs` integration into dashboard (job discovery UI)
- Cover letter editor in web app
- Resume version history (currently CLI-only in `~/.linkright/runs/`)
- Story bank UI (show STAR stories in web app after Pillar 3 ships)

---

## Pillar 4 — Content (Deferred Post-v1)

- LinkedIn content pipeline from career signals
- Turn daily work into authentic LinkedIn posts
- Source: career nuggets → content ideas → draft → schedule

---

## Browser Extension (v2)

*Spec: `specs/wave-8-extension-spec.md` (April 2026)*

Architecture: in-browser passive capture + autofill + memory overlay.

**Wave 8 components:**
1. **Job Capture** — intercept job posting pages, extract JD, send to CLI store
2. **Autofill** — fill job application forms using career profile data
3. **Memory Overlay** — show career nugget matches while reading a JD in browser
4. **Passive Capture** — background capture on every portal visit (Sprint C)

**Why deferred:** Extension distribution (Chrome Web Store review), maintenance overhead, and need for CLI+Website foundation first. Revisit after v1 public release.

---

## Platform Ideas (Long-Term Brainstorm)

*From context/ideas/ — not committed, just captured.*

### Job Seeker Automations
- Gmail → Job Tracker: AI extracts job details from emails, auto-generates application Kanban
- Naukri.com daily auto-upload (keeps profile "fresh" without manual login)
- LinkedIn auto-apply with cover letter generation
- GitHub Actions: LaTeX resume → PDF auto-build → GitHub Pages deploy

### AI PM Automations
- PRD generator from voice notes
- Sprint planning from backlog + capacity data
- Stakeholder update auto-draft from Jira/Linear
- Feature flag analysis: measure A/B test significance automatically

### Content Creator Automations
- Twitter/LinkedIn cross-post with format adaptation
- Blog post → LinkedIn carousel → Twitter thread pipeline
- Engagement analytics → content strategy recommendations

### Portfolio Automation
- Auto-generate portfolio website from GitHub repos + career signals
- "Why hire me" deck generator per target company (uses brand colors + JD alignment)

---

## Infrastructure Growth Path

```
Now (1 user, Rs.0)
  → Month 3–6 (Open Source, Rs.0)
  → Month 6–12 (1K–10K users, $200–500/mo: MongoDB Atlas Flex + Oracle paid)
  → Year 2+ (100K+ users, $10K+/mo: Atlas M30-M40, Redis Streams, CDN)
```

Key scaling triggers:
- >1 concurrent user → add Redis Streams for event queue
- >1K users → MongoDB Atlas Flex ($8–30/mo)
- >10K users → Oracle paid compute, CDN for PDF delivery
- >100K users → Qdrant Cloud for vector search, Atlas M30-M40
