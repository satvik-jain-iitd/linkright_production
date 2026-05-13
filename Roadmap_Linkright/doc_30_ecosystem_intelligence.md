# DOC 30 — Ecosystem Intelligence

## 1. Purpose

This document defines the ecosystem intelligence architecture for Linkright.

It specifies:

- ecosystem intelligence philosophy
- what ecosystem intelligence covers
- data sources
- company intelligence model
- archetype demand index
- ecosystem trust map
- market timing guidance
- privacy model
- phase scoping
- integration points

This document defines the external market context layer of Linkright.

---

# 2. Core Philosophy

Career decisions made in isolation miss market context.

A candidate may have a strong profile, strong positioning, and strong artifacts — and still make poor career decisions because they lack visibility into what is happening outside their current company.

Ecosystem intelligence answers questions that no resume system alone can answer:
- Who is hiring, and for what archetypes?
- Is demand for my specific PM subtype rising or falling?
- Which companies in my trust network currently have open roles?
- Is now a good time to move, or should I compound at my current company?

The fundamental principle:

```text
Career navigation without market context is navigation with eyes closed.
```

Ecosystem intelligence surfaces the external signal layer that makes timing and targeting decisions defensible.

---

# 3. What Ecosystem Intelligence Covers

Ecosystem intelligence has four coverage areas:

### 3.1 Company Hiring Signals

Who is hiring, at what velocity, and for which role archetypes.

A company that opened 12 PM roles in 60 days is different from one that opened 2.
A company hiring for AI PM is different from one hiring for growth PM.
Hiring velocity signals organizational expansion, product bets, and team gaps.

### 3.2 Archetype Demand Trends

Which PM subtypes are rising or falling in demand across the captured market.

Examples of PM archetypes tracked:
- AI PM
- Growth PM
- Platform PM
- Infra PM
- B2B enterprise PM
- Founder-track / operator-style PM

Archetype demand can shift in 60–90 day windows as market conditions, funding cycles, and AI adoption cycles evolve.

### 3.3 Ecosystem Trust Networks

Which companies and people are interconnected in the user's network.

Startup ecosystems are not anonymous markets. Opportunity flow often follows trust proximity. Understanding which nodes in the user's network are connected to target companies enables warm intro path suggestions.

### 3.4 Market Timing Signals

When to explore externally, and when to stay and compound.

Market timing combines hiring velocity, the user's promotion readiness, and archetype demand trends into a directional signal. This is not a prediction — it is a structured summary of conditions the user can act on.

---

# 4. Data Sources

Ecosystem intelligence is built from three source types:

### 4.1 Passive Browser Extension Capture

Job postings encountered during the user's normal browsing are captured automatically via the browser extension (DOC 09).

This is the primary input channel. It is:
- zero-effort for the user
- contextually relevant (the user was already looking)
- high signal density (postings the user considers are more relevant than random market scans)

Captured postings feed the company intelligence model and archetype demand index.

### 4.2 Weekly Market Review Inputs

During the user's weekly review session (DOC 26), they may surface signals manually:
- roles they researched
- companies they evaluated
- trends they noticed
- conversations they had

These inputs are low-volume but high-quality. They reflect the user's active market awareness.

### 4.3 Public Signal Lookups

User-initiated lookups of public data:
- Crunchbase funding events
- LinkedIn job count trends (user-accessed, not scraped)
- company news or product announcements

These are triggered by the user or by the system surfacing a "check this" prompt during the weekly review. The system does not autonomously scrape or continuously monitor public sources.

---

# 5. Company Intelligence Model

For each company encountered in the ecosystem, the system maintains a structured intelligence record:

- **hiring_velocity**: pace of new PM-relevant job postings in the last 30 / 60 / 90 days
- **pm_archetype_demand**: which PM subtypes are being hired for (inferred from JD parsing)
- **known_culture_signals**: observed signals about pace, structure, autonomy, AI adoption
- **trust_network_nodes**: contacts the user has at this company (from profile and relationship graph)
- **recent_funding_stage**: last known funding round and approximate stage
- **last_updated**: timestamp of most recent signal capture

Company records are built incrementally. Early records are sparse. Records become richer over time as more signals accumulate.

Company intelligence is stored in Oracle Postgres (job/market data), not Supabase (user PII only).

---

# 6. Archetype Demand Index

The archetype demand index tracks signal frequency across all captured JDs, segmented by PM subtype.

The index answers:
- Which PM archetypes appear most frequently in recently captured postings?
- How has frequency changed over the last 30 / 60 / 90 days?
- Which archetypes are growing, flat, or declining?

Example output:

```text
AI PM: +23% demand signal in last 60 days (n=47 postings)
Growth PM: flat (n=31 postings)
Enterprise B2B PM: -8% (n=19 postings)
```

The index is refreshed incrementally as new postings are captured. It does not require a batch rebuild.

The archetype demand index is not a prediction. It is a frequency summary of what the user has encountered in the market.

---

# 7. Ecosystem Trust Map

The ecosystem trust map models the interconnections between companies and people in the user's network.

It is built from:
- the user's relationship graph (DOC 25)
- captured postings at companies where the user has contacts
- companies associated with the user's former colleagues and managers

The trust map enables:
- warm intro path suggestions ("you know X at Company Y — they have an open AI PM role")
- second-degree connection visibility ("X worked with Y who is now hiring at Z")
- ecosystem clustering (which companies orbit similar founder / investor / operator circles)

The trust map is used by the relationship graph (DOC 25) for intro path suggestions and by the career decision engine (DOC 23) for opportunity prioritization.

Phase 1 builds a basic version. The full trust map — with ecosystem clustering and second-degree path reasoning — is a Phase 2 capability.

---

# 8. Market Timing Guidance

Market timing guidance combines three inputs:

1. **Hiring velocity** from the company intelligence model (is the market actively open?)
2. **User's promotion readiness** from DOC 27 (has the user compounded enough to move with leverage?)
3. **Archetype demand index** (is the user's archetype in demand right now?)

The combination produces a directional signal:

```text
Good time to explore externally:
- hiring velocity high
- user archetype in demand
- user has 6+ months of recent strong signal

Stay and compound:
- archetype demand soft
- user tenure under 12 months at current role
- no strong recent wins to narrate
```

Market timing guidance is surfaced during the weekly review (DOC 26) and the career decision engine (DOC 23). It is directional, not prescriptive. The user makes the final call.

---

# 9. Privacy Model

All ecosystem intelligence is derived from:
- the user's own browsing captures
- the user's own review inputs
- public signals the user accesses

There is no cross-user data. The system never pools job market data across users or builds market intelligence by aggregating behavior across accounts.

No ecosystem data is sold or shared.

The user owns their ecosystem intelligence record. It can be exported, inspected, and deleted.

---

# 10. Phase Scoping

### Phase 1

- Company intelligence model (hiring velocity + archetype demand per company)
- Archetype demand index (cross-company trend tracking)
- Basic trust map (first-degree connections only)
- Market timing signal (simple directional output)

### Phase 2

- Full ecosystem trust map (second-degree paths, ecosystem clustering)
- Funding-stage-aware opportunity scoring
- Richer market timing with historical pattern analysis
- VC firm ecosystem modeling (which firms create talent-dense ecosystems)

---

# 11. Integration Points

This document integrates with:

- **DOC 04 — Opportunity Lifecycle & Workflow Architecture**: opportunity targeting uses company intelligence to prioritize which roles to pursue. Archetype demand index informs which opportunities align with market conditions.
- **DOC 09 — Browser Extension & Ambient Intelligence Layer**: the extension is the passive capture mechanism. Every JD the user encounters is a potential ecosystem data point.
- **DOC 23 — Career Decision Engine**: the decision engine pulls market timing signals and company intelligence to add external context to role comparison and career navigation decisions.
- **DOC 25 — Relationship Graph**: the trust map is built on top of the relationship graph. Ecosystem connections are surfaced as warm intro paths during opportunity targeting.
- **DOC 26 — Weekly Review**: the weekly review is the primary human-in-the-loop checkpoint for ecosystem intelligence. Market signals are surfaced, confirmed, and updated during review sessions.

---

# 12. Ecosystem Intelligence Boundaries

This document defines:
- ecosystem intelligence philosophy
- data source architecture
- company intelligence model
- archetype demand index
- ecosystem trust map
- market timing guidance
- privacy model

It does not define:
- relationship graph internals
- browser extension architecture
- career decision engine logic
- retrieval systems
- profile memory architecture

Those belong to other documents.

---

# 13. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 04 — Opportunity Lifecycle & Workflow Architecture
- DOC 09 — Browser Extension & Ambient Intelligence Layer
- DOC 12 — Career Navigation Intelligence & Long-Term Compounding System

This document influences:
- DOC 23 — Career Decision Engine
- DOC 25 — Relationship Graph
- DOC 26 — Weekly Review

This document should be treated as the canonical ecosystem intelligence reference for Linkright.
