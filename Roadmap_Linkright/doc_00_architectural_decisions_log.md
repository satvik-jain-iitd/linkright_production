# DOC 00 — Architectural Decisions Log
*Locked: 2026-05-13 | All decisions confirmed by product owner*

This document records all locked architectural decisions for LinkRight. Every other doc in this system must be consistent with these decisions. If a decision is revisited, update this doc first.

---

## Decision 1 — Product Scope

**Decision:** Full career lifecycle
**Covers:** Resume → Application → Interview → Offer → Onboarding → Performance → Promotion → Career pivot
**Rejected:** "Offer only" (too limited), "90 days only" (artificial boundary)
**Implication:** DOC 27 (Post-Offer OS), DOC 28 (Identity Evolution), DOC 12 (Long-Term) all apply. System is a career OS, not a job search tool.

---

## Decision 2 — Automation Philosophy

**Decision:** Semi-autonomous — human approves, system executes
**Pattern:** System proposes plan → User reviews + approves → System executes
**Rejected:** "Always suggest only" (too slow, poor UX), "Fully autonomous" (high risk for career decisions)
**Implication:** Every action-triggering workflow (apply, follow up, send message, update profile) must have an approval gate. Default = suggest, not execute. n8n orchestrates; human gates the transitions.

---

## Decision 3 — Layout Engine

**Decision:** Pixel math first (deterministic), fallback to hybrid if deterministic fails
**Pattern:** Font metrics × character count = pixel width. No LLM for layout decisions. If deterministic alone can't solve an edge case, add LLM content + deterministic validation as fallback.
**Rejected:** "LLM-only layout" (non-deterministic, unpredictable PDF output)
**Implication:** DOC 16 (Layout Engine) must spec pixel budget algorithm first. LLM = content generation only. Deterministic = all spatial decisions.

---

## Decision 4 — Closed-Loop Learning

**Decision:** Implicit conversion tracking
**Pattern:** System silently tracks: application sent → response received → interview scheduled → offer made. No user friction. Outcome signal feeds back into retrieval ranking and bullet scoring.
**Rejected:** "Manual feedback only" (high friction, low compliance), "A/B testing" (needs volume, premature)
**Implication:** DOC 24 (Closed-Loop Learning) must spec outcome event schema and how conversion rates feed signal weights. Explicit feedback added later as layer 2.

---

## Decision 5 — Career Decision Engine

**Decision:** Simple job comparison (MVP)
**Pattern:** Job A vs Job B scored on key dimensions: comp, growth trajectory, brand, culture fit, skill development, alignment with archetype. Visual comparison + recommendation.
**Rejected:** "Career path modeling" (needs historical data), "Market intelligence" (needs external APIs, high build cost)
**Implication:** DOC 23 (Career Decision Engine) scoped to pairwise comparison first. Path modeling and market intelligence = Phase 2 extensions.

---

## Decision 6 — Relationship Graph

**Decision:** AI-suggested connections
**Pattern:** Based on target companies + career goals, system suggests "you should connect with [type of person] at [company]". User manually logs actual connections. No auto-import.
**Rejected:** "Manual only" (too passive), "Auto-extract from LinkedIn/email" (ToS violations + privacy risk)
**Implication:** DOC 25 (Relationship Graph) is a suggestion engine, not a CRM. Data is sparse and user-controlled. Trust graph grows via explicit user confirmation only.

---

## Decision 7 — Personal Operating Rhythm

**Decision:** Structured weekly review
**Pattern:** System sends weekly career check-in prompt (5 questions, ~15 min). Topics: applications status, follow-ups due, skills to develop, wins to document, market signals noticed. Habit loop: cue → routine → reward (clarity).
**Rejected:** "On-demand only" (low retention), "Proactive ambient" (Phase 2, needs integrations)
**Implication:** DOC 26 (Personal Rhythm) specs the weekly review template, question bank, and how responses feed the memory graph. Ambient intelligence = future layer.

---

## Decision 8 — Privacy + Storage Architecture

**Decision:** Local-first + optional encrypted MongoDB cloud backup
**Storage stack:**
- Local: JSON files / SQLite on device (existing CLI model, unchanged)
- Cloud backup: MongoDB Community Edition (self-hosted or Atlas free tier)
  - End-to-end encrypted — only user can decrypt
  - Document model = natural fit for career profile JSON
  - Built-in vector search = replaces pgvector for cloud layer (storage + search only — embedding model NOT included; fastembed/Jina still generates the vectors)
- Website/worker (sync-resume-engine): Supabase stays — separate domain, not changing
- Oracle Postgres: stays for jobs/analytics — separate domain, not changing
**Rejected:** "Cloud-first" (trust hurdle too high for salary + rejection data)
**Implication:** DOC 13 (Storage Infrastructure) must spec MongoDB schema + encryption approach. CLI local storage unchanged. Cloud sync = opt-in, user-initiated.

---

## Decision 9 — Identity Evolution

**Decision:** System suggests identity upgrade, user approves
**Pattern:** System monitors signals (new title mentioned in diary, skills added, tenure crossed threshold) and surfaces: "Based on your signals, you seem to be operating at Director level. Update your profile?" User confirms or dismisses.
**Rejected:** "Manual only" (stale profiles = bad resume output), "Automatic" (risk of wrong archetype = interview mismatch)
**Implication:** DOC 28 (Identity Evolution) must spec signal detection logic for level transitions + PM archetype evolution. Suggestion is low-stakes; system never auto-updates identity without confirmation.

---

## Summary Table

| # | Decision | Choice |
|---|----------|--------|
| 1 | Scope | Full career lifecycle |
| 2 | Automation | Semi-autonomous (approve → execute) |
| 3 | Layout | Pixel math first, hybrid fallback |
| 4 | Learning | Implicit conversion tracking |
| 5 | Decision Engine | Simple job comparison (MVP) |
| 6 | Relationship Graph | AI-suggested connections |
| 7 | Operating Rhythm | Structured weekly review |
| 8 | Storage | Local + MongoDB encrypted cloud |
| 9 | Identity | System suggests, user approves |
