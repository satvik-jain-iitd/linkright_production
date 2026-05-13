# DOC 24 — Closed-Loop Learning System

## 1. Purpose

This document defines the closed-loop learning architecture for Linkright.

It specifies:

- learning philosophy
- outcome event pipeline
- signal weight updates from outcomes
- conversion funnel tracking
- learning boundaries and safeguards
- explicit feedback layer design (Phase 2)
- privacy constraints
- integration with retrieval, generation, and career decision systems

This document defines how Linkright gets better over time without asking the user to manually rate or evaluate anything.

---

## 2. Core Learning Philosophy

The system learns from what actually happened.

Not from what the user said about it.

Implicit conversion signals are more reliable than explicit ratings because:
- users rate inconsistently
- users rate when in emotional states
- ratings add friction that reduces adherence
- outcomes are objective: an employer either responded or did not

The learning hierarchy is:

```text
Outcome events (strongest signal)
→ Behavioral patterns across opportunities
→ Explicit user feedback (Phase 2, supplementary)
```

Explicit feedback will be added in Phase 2.

It should never override implicit outcome signals.

It may amplify or inform them.

---

## 3. Outcome Event Pipeline

Every meaningful step in an application lifecycle is an event.

The canonical outcome event sequence:

```text
application_sent
→ employer_response
→ interview_scheduled
→ interview_completed
→ offer_received
→ accepted | declined | no_response
```

Each event is a data point.

Each event carries:
- timestamp
- opportunity ID
- opportunity metadata (company type, role archetype, seniority level)
- profile version used at time of event
- resume version used at time of event
- signal set active at time of event

These events are stored append-only in `~/.linkright/outcomes/outcome_events.jsonl`.

They are never mutated after writing.

If an event is corrected, a new event is written with a correction flag.

---

## 4. What the System Learns From Outcomes

### 4.1 Which Resume Version Got a Response

When `employer_response` follows `application_sent`:
- the system records the resume version that was active
- it records the signal weights that drove bullet selection for that version
- it increments confidence scores for those signals relative to that opportunity type

This is an inferred signal.

The system cannot know for certain which bullet caused the response.

But it can observe that a particular signal combination correlated with a response at a particular company type.

Over many outcomes, patterns become statistically meaningful.

### 4.2 Which Signal Combinations Led to Interviews

When `interview_scheduled` follows `employer_response`:
- the system compares the active signal set across all application-to-interview conversions
- it identifies which signal clusters appear more often in converted sequences
- it increases retrieval weight for those signals in similar opportunity contexts

### 4.3 Which Archetypes Succeeded at Which Company Types

The system tracks conversion rates per:
- candidate archetype (execution PM, growth PM, technical PM, etc.)
- company type (early startup, series B, enterprise, BigTech)
- role family (platform, consumer, B2B, AI-native)

If a user's archetype consistently converts at one company type but not another, the system surfaces this pattern.

This informs opportunity targeting (DOC 12) and career decision support (DOC 23).

---

## 5. Signal Weight Updates

Signal weights govern which evidence gets retrieved and prioritized during resume generation (DOC 05, DOC 06).

Outcome events feed back into signal weights through a slow, conservative update mechanism.

The update model:

```text
On employer_response:
  signals active in that resume version → small positive weight nudge

On no_response after 21 days:
  signals active → small negative weight nudge

On interview_scheduled:
  signals active → moderate positive weight nudge

On offer_received:
  signals active → strong positive weight nudge
```

Weight nudges are:
- small by default
- bounded (no signal can dominate through a single outcome)
- reversible (weights decay toward baseline over time if not reinforced)

The system must not overfit to a single string of events.

A single rejection does not mean a signal is wrong.

A pattern across many outcomes is meaningful.

---

## 6. Conversion Funnel Tracking

The system tracks conversion rates across the full funnel:

```text
Applications sent
→ employer response rate                   (application → response)
→ interview schedule rate                  (response → interview)
→ offer rate                               (interview → offer)
```

These are computed:
- per company type
- per role archetype
- per resume version
- per time window

The purpose of funnel tracking is diagnosis, not judgment.

If application-to-response rate is low, the positioning or targeting may be the issue.

If response-to-interview rate is low, the recruiter screen experience may be the issue.

If interview-to-offer rate is low, the signal content or story structure may be the issue.

The system surfaces these patterns.

The user decides what to do.

---

## 7. Learning Boundaries

The system must not learn in all directions.

Some learning is harmful or destabilizing.

### 7.1 Do Not Rewrite Identity Based on Rejections

If a user receives multiple rejections from one company type, the system should not:
- automatically reframe the user's archetype
- suppress signals that define the user's real experience
- suggest identity changes without the user explicitly engaging

Rejection at BigTech does not mean the user should stop positioning as an AI PM.

The system may surface a pattern.

The user decides whether to act on it.

Identity evolution is always user-initiated (DOC 01 section 9).

### 7.2 Do Not Overfit to One Company Type

If a user receives several conversions at one company type in a row:
- the system should not narrow the retrieval context to only serve that type
- the user's full signal breadth must remain accessible

Specialization is valid when the user decides it.

Specialization imposed by overfitting is a trap.

### 7.3 Do Not Learn From Single Events

Single outcomes are noisy.

The system should require:
- minimum 3 same-type events before adjusting weights materially
- minimum 5 same-type events before surfacing pattern as a recommendation

Below those thresholds, outcome events are stored but not acted upon.

---

## 8. Explicit Feedback Layer (Phase 2)

Phase 2 adds the ability for users to provide ratings on top of implicit signals.

The design:

```text
After each completed interview:
  System asks (optionally): "How did that feel? Any signals that worked?"
  User may respond or skip.
  If responded: structured feedback is stored alongside the implicit outcome event.
```

Explicit feedback does not override implicit signals.

It provides an additional layer of context.

Examples of useful explicit feedback:
- "The cross-functional influence story landed well"
- "They seemed unimpressed by the AML compliance bullet"
- "The startup track framing resonated immediately"

This data is stored as annotated outcome events.

It feeds into the same signal weight system with additional context tags.

The interface should be low-friction.

Explicit feedback should never be required.

---

## 9. Privacy

Outcome data is personal.

It contains career history, compensation hints, rejection history, and interview progression.

Privacy rules:
- outcome events are stored locally by default
- if cloud sync is enabled, outcome events are encrypted before push (DOC 13)
- outcome events are NEVER shared across users
- the system has no cross-user learning layer
- no telemetry is sent to any external service

Every user's learning state is entirely their own.

Cross-user signal aggregation is not a goal of Linkright.

The system compounds the individual user's intelligence.

It does not build a shared intelligence layer.

---

## 10. Integration

The closed-loop learning system integrates with:

### DOC 05 — Retrieval & Ranking

Signal weights produced by outcome learning feed directly into retrieval scoring.

Higher-weighted signals are retrieved with higher priority when building resume context for similar opportunity types.

### DOC 06 — Resume Generation

Signal weight state at generation time determines which evidence is surfaced and how bullets are prioritized.

Outcome learning gradually improves the strategic relevance of generated artifacts.

### DOC 23 — Career Decision Engine

Conversion funnel data and archetype-performance patterns feed into opportunity ranking and career trajectory advice.

The decision engine uses outcome patterns to help users evaluate whether a target opportunity type is likely to convert.

### DOC 12 — Career Navigation Intelligence

Long-run outcome patterns feed into the compounding intelligence layer.

Over time, the system becomes aware of:
- which market segments the user converts in
- which signal types produce the most durable pipeline performance
- how the user's positioning has evolved across job search cycles

---

## 11. Observability

Outcome events and weight updates should be fully observable.

The user should be able to inspect:
- what outcome events have been recorded
- how signal weights have changed since last job search
- which conversion patterns the system has detected
- what the current funnel performance looks like

This is consistent with DOC 11.

Relevant commands:

```text
linkright outcomes list                      # view outcome event log
linkright outcomes funnel                    # view conversion rates by stage
linkright signals weights                    # view current signal weights
linkright signals history --since <date>     # view weight changes over time
```

The learning state should never be a black box.

---

## 12. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 05 — Retrieval, Ranking & Strategic Intelligence System
- DOC 06 — Resume, Positioning & Artifact Generation Engine
- DOC 11 — Observability, Logging & Explainability Framework
- DOC 13 — Storage Infrastructure
- DOC 13A — Implementation Architecture Documentation Topology & Governance Plan

This document influences:
- DOC 14 — Canonical Schemas, Entity Contracts & State Models
- DOC 23 — Career Decision Engine
- DOC 12 — Career Navigation Intelligence & Long-Term Compounding System

This document should be treated as the canonical closed-loop learning system reference for Linkright.
