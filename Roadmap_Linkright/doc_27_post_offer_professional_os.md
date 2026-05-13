# DOC 27 — Post-Offer Professional OS

## 1. Purpose

This document defines the post-offer, in-role intelligence layer of Linkright.

It specifies:

- the philosophy of career capital compounding after joining
- 30-60-90 day plan generation
- manager alignment intelligence
- internal advocacy building with colleagues who were formerly part of the hiring process
- performance signal capture and memory compounding
- promotion readiness tracking
- internal mobility workflows
- career pivot detection
- integration with the broader Linkright system

This document defines how Linkright extends its usefulness past the moment of offer acceptance.

---

## 2. Core Philosophy

The offer is not the destination.

It is the starting line.

Most career navigation systems treat offer acceptance as an endpoint.
Linkright treats it as a context switch.

The same compounding logic that made the job search effective — evidence accumulation, signal strengthening, identity coherence — continues to apply after the candidate joins.

The difference is:

- Before the offer, signals feed positioning artifacts.
- After the offer, signals feed career capital that will power the next move, the internal promotion case, the performance conversation, and eventually the narrative for the following search.

Career capital compounds most powerfully inside a role.

Linkright should capture that compounding in real time, not reconstruct it months later when the user is already searching again.

---

## 3. 30-60-90 Day Plan Generation

When a user accepts an offer, Linkright can generate a structured first-90-days playbook.

Inputs:

- role type and seniority level
- company size and stage
- user archetype from DOC 28
- signals about the team's operating environment (from JD context and any available company intelligence)
- user's historical strengths from the memory graph in DOC 03

Structure of the generated playbook:

### Days 1-30: Listen and Map

- Stakeholder identification: who are the decision-makers, the informal influencers, the key collaborators?
- Communication style observation: how does the team actually communicate versus how the company claims to communicate?
- Early trust signals: who might become an internal sponsor?
- Expectation alignment: what does the manager actually want from this role in the first 30 days?

### Days 31-60: Build and Demonstrate

- Identify one high-visibility quick win that is achievable within existing constraints.
- Begin connecting work to measurable outcomes.
- Establish a rhythm with the manager: what are the preferred communication formats, escalation preferences, and feedback channels?
- Start mapping informal influence networks.

### Days 61-90: Align and Signal

- Synthesize observations into a written alignment document shared with the manager.
- Establish which projects will define the performance period.
- Begin proactively managing up: surface strategic awareness, not just tactical execution.
- Calibrate whether initial expectations are accurate or require renegotiation.

The playbook is not prescriptive.
It is adaptive to the user's archetype, the organizational environment, and the logged evidence from earlier diary entries.

---

## 4. Manager Alignment Intelligence

Early manager alignment is one of the highest-leverage activities in any new role.

The system should help the user reason about:

- what the manager is optimizing for in their own career
- what communication style tends to reduce friction with this manager type
- what outcomes will make the manager's position stronger
- how to sequence early conversations to establish trust

Alignment intelligence draws from:

- role context and seniority signals
- organizational position of the manager (do they need visibility upward, or do they need execution reliability?)
- archetype inference from available signals

The system surfaces suggestions, not instructions.

The user confirms, adjusts, or dismisses each recommendation.

Manager alignment intelligence should feel like a strategic thinking partner, not a behavior script.

---

## 5. Internal Advocacy Building

When the user joins, former members of the hiring committee become colleagues.

This is a structural advantage that most professionals underutilize.

The system should help the user reason about:

- which colleagues were part of the hiring process
- what signals those people formed during the interview loop
- how to translate initial hiring credibility into ongoing internal trust
- which stakeholders are worth investing in early

Internal advocacy building is not manipulation.
It is understanding that organizational trust compounds through repeated reliable behavior, and that the hiring loop already established some initial trust that is worth preserving.

The system does not generate outreach scripts for this layer.
It surfaces strategic awareness: who matters, what they observed, and how continued consistency strengthens credibility.

---

## 6. Performance Signal Capture

Performance evidence decays.

Wins from six months ago are often difficult to reconstruct in detail.
Challenges that shaped judgment are forgotten before they can be articulated.

Linkright should prompt the user weekly (via the personal rhythm layer in DOC 26) to log:

- wins and outcomes from the past week
- challenges encountered and how they were navigated
- new responsibilities that emerged
- any feedback received from manager or stakeholders
- any skills or tools applied that were not part of the original profile

These entries are processed and stored in the memory graph (DOC 03) as dated evidence nodes.

Over time, this creates a high-fidelity career log that:

- feeds future resume bullets with specific evidence rather than vague recollections
- strengthens signal confidence scores
- surfaces identity evolution signals for DOC 28
- provides the raw material for promotion cases, performance reviews, and future positioning

The capture is lightweight.
The compounding is substantial.

---

## 7. Promotion Readiness System

At any point, the user can ask Linkright: "Am I ready for promotion?"

The system should not answer this with a generic framework.
It should reason from the user's actual accumulated evidence against a model of what the target level requires.

Inputs:

- user's current seniority level from DOC 28
- target level signals
- logged performance evidence from the weekly rhythm
- signal graph from DOC 03

Output:

A structured readiness assessment of the form:

```text
You have strong evidence for: strategic communication, ambiguity handling, cross-functional coordination.
You have moderate evidence for: managing junior PMs, portfolio-level reasoning.
You have weak or missing evidence for: organizational influence at scale, VP-visible wins.
```

The system then suggests:

- what evidence would close the gap
- which current projects are most likely to produce that evidence
- which signals to prioritize logging in upcoming weeks

The promotion readiness system is not a performance management tool.
It is a strategic awareness layer for the user.

The system does not interact with the manager.
It does not generate performance review text automatically.
It helps the user see the gap clearly so they can close it deliberately.

---

## 8. Internal Mobility

When the user considers moving to a different team, department, or function within the same company, the system should treat the internal opportunity with the same rigor as an external one.

Internal mobility re-runs the opportunity lifecycle from DOC 04:

- internal JD or role description parsing
- fit scoring against the current profile
- signal mapping
- artifact generation tailored to the internal context
- stakeholder analysis for the internal hiring committee

Internal mobility often requires different positioning than external.
The user is known internally.
That means the positioning must acknowledge existing reputation while introducing new signals relevant to the target role.

The system surfaces this distinction explicitly.

---

## 9. Career Pivot Detection

Not every career trajectory continues in a straight line.

The system should monitor accumulated signals over time and surface a prompt if patterns suggest misalignment between the user's actual work and their stated archetype, or between the role environment and the user's strongest signals.

Detection triggers may include:

- repeated diary entries expressing misalignment, disengagement, or strategic frustration
- significant skill accumulation in a direction different from the current archetype
- tenure signals crossing a threshold without corresponding growth evidence
- strong signals pointing to a different PM subtype than the current profile

When a detection trigger fires, the system surfaces a single prompt:

```text
Based on signals from recent weeks, your strongest evidence may be building in a direction different from your current archetype.
Worth reviewing your profile?
```

The user can confirm the observation, dismiss it, or defer review by four weeks.

The system does not reassign the user's identity.
It surfaces the pattern.

Career pivot detection is distinct from identity evolution in DOC 28.
Pivot detection is about whether the role itself is the right fit.
Identity evolution is about whether the user's seniority level or archetype has changed.

---

## 10. Non-Goals

This document explicitly does not cover:

- performance review generation for the manager's use
- manager-facing reporting or evaluation tools
- compensation benchmarking (that belongs to the negotiation layer)
- professional learning recommendations beyond what the signal gap analysis surfaces
- autonomous work tracking without user-initiated input

The Post-Offer Professional OS is a user-side system.
The user's manager never sees it.
The user retains full control over what gets captured and what gets surfaced.

---

## 11. Integration

This document integrates with:

- DOC 03 — Canonical Profile & Memory Graph: weekly diary entries feed directly into the memory graph as dated evidence
- DOC 04 — Opportunity Lifecycle: internal mobility re-runs the opportunity lifecycle for internal roles
- DOC 06 — Resume Generation: performance signal capture provides the evidence pool for future resume tailoring
- DOC 26 — Personal Operating Rhythm: the weekly review is the primary input mechanism for performance capture
- DOC 28 — Identity Evolution System: tenure signals and responsibility patterns from this layer are the primary input to identity upgrade detection

---

## 12. Document Dependencies

This document depends on:

- DOC 01 — Vision, Philosophy & System Principles
- DOC 02 — Core Ontology & Semantic Architecture
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 04 — Opportunity Lifecycle & Workflow Architecture
- DOC 12 — Career Navigation Intelligence & Long-Term Compounding System
- DOC 26 — Personal Operating Rhythm & Weekly Review System
- DOC 28 — Identity Evolution System

This document should be treated as the canonical reference for post-offer career intelligence in Linkright.
