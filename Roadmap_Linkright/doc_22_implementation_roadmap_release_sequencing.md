# DOC 22 — Implementation Roadmap & Release Sequencing

## 1. Purpose

This document defines the release sequence, dependency ordering, and scope boundaries for Linkright across its planned versions.

It specifies:

- release philosophy
- v1 scope and current state
- v1.1 through v2.1+ roadmap
- dependency rules between documents and components
- non-goals and scope guards

This document is directional. It describes what ships in what order and why. It does not assign dates. Sprint-level planning lives in beads issues.

---

## 2. Release Philosophy

Ship working software incrementally.

Documentation is a planning artifact, not a delivery gate. A document being written does not mean a feature is ready to build. A feature being built does not require every related document to be finalized first.

The sequence below reflects two priorities:

1. Core value first — resume tailoring, JD analysis, and profile memory are the foundation. Everything else compounds on top of them.
2. Dependency order — some systems cannot be built correctly until their inputs are stable. Those dependencies are called out explicitly.

The system should avoid building compounding systems before their input signals are flowing. A learning system with no outcome data to learn from is infrastructure overhead, not user value.

---

## 3. v1 — Core Career Artifact System

**Status: Shipped or in active progress.**

Scope:

- Resume tailoring pipeline (JD analysis → signal retrieval → generation → validation → PDF)
- JD analysis and fit scoring
- Canonical profile memory (local-first, JSON/SQLite)
- Basic retrieval from profile signals
- PDF generation and layout engine (deterministic width math)
- CLI UX (setup wizard, profile create, resume tailor, critique)
- Multi-key LLM setup (free-tier first)
- Output quality validation (width, schema, authenticity checks)
- Observability foundation (run logs, artifact lineage)

This version establishes the execution substrate that every later version depends on.

---

## 4. v1.1 — Quality and Learning Foundation

**Dependencies: v1 stable.**

Scope:

- Closed-loop learning baseline (DOC 24) — outcome event schema, implicit conversion tracking, signal weight update pipeline
- Evaluation framework baseline (DOC 18) — per-step quality metrics, eval harness, baseline scores per pipeline stage
- Layout engine hardening (DOC 16) — pixel budget algorithm completeness, edge case coverage, fallback hybrid handling

Rationale: before expanding feature scope, establish the measurement and learning infrastructure that makes future iterations improvable. The evaluation framework is what separates a system that gets better from a system that gets bigger.

---

## 5. v1.2 — Career Decision and Post-Offer Layer

**Dependencies: v1.1 outcome events flowing, profile memory stable.**

Scope:

- Career decision engine MVP (DOC 23) — pairwise job comparison on comp, growth, brand, culture fit, skill development, archetype alignment
- Post-offer OS basics (DOC 27) — 30-60-90 day plan generation seeded from offer context and company signals
- Personal rhythm weekly review (DOC 26) — weekly check-in template, question bank, response ingestion into memory graph

Rationale: the resume-to-offer pipeline is functional by v1.1. v1.2 adds value at two adjacent career moments: the decision before accepting an offer, and the onboarding after accepting one. The weekly review also begins building the habit loop that makes the memory graph self-improving.

---

## 6. v1.3 — Network and Identity Intelligence

**Dependencies: v1.2 weekly review data flowing, profile memory has longitudinal signal history.**

Scope:

- Relationship graph MVP (DOC 25) — AI-suggested connection candidates based on target companies and career goals; user-logged actual connections; suggestion engine, not a CRM
- Identity evolution signal tracking (DOC 28) — signal detection for level transitions and PM archetype evolution; suggestion surfacing with user confirmation gate
- Ecosystem intelligence Phase 1 (DOC 30) — market signal ingestion, company intelligence enrichment, role trend awareness

Rationale: networking and identity signals require longitudinal data to be useful. Building them before the weekly review habit loop and outcome tracking are stable would produce a sparse, low-signal system. v1.3 is the right moment because by then the memory graph has history.

---

## 7. v2.0 — Ambient and Cloud Layer

**Dependencies: v1.x workflows stable, user trust established through v1 experience.**

Scope:

- Browser extension Phase 1 (DOC 20) — JD capture from job boards, contextual autofill assistance, opportunity-state triggers via extension
- MongoDB cloud backup (DOC 13) — opt-in encrypted cloud sync of profile and opportunity data; document model aligned with career profile JSON; built-in vector search for cloud retrieval layer
- Trust governance full (DOC 29) — explicit permission model for what the system may do autonomously, what requires approval, and what is always manual

Rationale: the browser extension and cloud sync require user trust that is earned through v1 experience. Trust governance should be fully specified before ambient features ship, because ambient features are the first place where the system touches user state outside of explicit CLI invocations.

---

## 8. v2.1+ — Autonomous and Compounding Intelligence

**Dependencies: v2.0 trust governance and permission model in place.**

Scope may include:

- Ambient intelligence layer — contextual career guidance surfaced at the right moment without explicit invocation
- Autonomous agents Phase 2 — networking outreach, recruiter follow-up, calendar-based interview prep scheduling (see DOC 21, section 8)
- Multi-persona support — different positioning profiles for different target markets, maintained in parallel
- Full ecosystem intelligence (DOC 30) — market trend analysis, competitive positioning, hiring pattern signals

This scope is directional. Exact feature boundaries for v2.1+ are defined at sprint time, not here.

---

## 9. Dependency Rules

These rules govern what must be stable before a dependent system is built.

| Dependency | Required Before |
|---|---|
| DOC 14 (Data Schemas) stable | DOC 15 (Retrieval Implementation) locks |
| DOC 24 (Learning) outcome events flowing | Signal weights have meaningful data |
| DOC 04 (Opportunity Lifecycle) events defined | DOC 24 (Learning) ingestion pipeline works |
| DOC 26 (Weekly Rhythm) habit loop active | DOC 25 (Relationship Graph) has useful signal density |
| DOC 26 (Weekly Rhythm) data flowing | DOC 27 (Post-Offer OS) has lived-experience input |
| v1 execution substrate stable | Evaluation framework produces meaningful baselines |
| Trust governance (DOC 29) complete | Autonomous agents may ship |

These are not bureaucratic gates. They reflect real build-order risk. A system built before its inputs are stable will produce low-quality outputs and generate user distrust that is hard to recover from.

---

## 10. Non-Goals

This roadmap is directional, not a sprint plan.

Dates are not assigned here. Sprint planning and issue tracking live in beads. The roadmap describes sequence and dependency, not schedule.

Feature granularity below the release level is not specified here. Each release has a target scope; exact story decomposition happens at sprint time.

This document does not supersede other architecture documents. If a later document specifies a design constraint that affects sequencing, this document should be updated to reflect it. DOC 00 remains the canonical source of locked decisions.

---

## 11. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 00 — Architectural Decisions Log (all 9 decisions)

This document references (does not define):
- DOC 13 — Storage Infrastructure
- DOC 14 — Data Schemas
- DOC 15 — Retrieval Implementation
- DOC 16 — Layout Engine
- DOC 18 — Evaluation Framework
- DOC 20 — Browser Extension
- DOC 21 — Agent Governance (this series)
- DOC 23 — Career Decision Engine
- DOC 24 — Closed-Loop Learning
- DOC 25 — Relationship Graph
- DOC 26 — Personal Operating Rhythm
- DOC 27 — Post-Offer OS
- DOC 28 — Identity Evolution
- DOC 29 — Trust Governance
- DOC 30 — Ecosystem Intelligence

This document should be treated as the canonical release sequencing and implementation roadmap reference for Linkright.
