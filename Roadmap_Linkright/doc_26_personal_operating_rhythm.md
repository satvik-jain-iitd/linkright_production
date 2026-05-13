# DOC 26 — Personal Operating Rhythm

## 1. Purpose

This document defines the personal operating rhythm architecture for Linkright.

It specifies:

- operating rhythm philosophy
- weekly review structure
- habit loop design
- diary ingestion model
- how review data feeds the system
- monthly review design
- integration with memory, identity, and learning systems
- Phase 2 ambient intelligence direction
- non-goals and system boundaries

This document defines the career capital accumulation rhythm of Linkright.

---

## 2. Core Philosophy

Career management is a practice, not an event.

Most professionals treat career navigation reactively:
- update resume when unemployed
- network when urgently job-seeking
- reflect on skills when facing a performance review

This creates brittle, high-anxiety career management with no compounding advantage.

Strong operators treat career navigation as a consistent practice:
- small consistent inputs compound into significant strategic leverage over time
- weekly reflection surfaces signals that would otherwise be lost
- regular review creates a feedback loop between lived experience and system intelligence

The weekly rhythm is the mechanism by which:
- raw experience becomes structured evidence
- wins become future resume bullets
- skill gaps become profile update signals
- market observations become opportunity targeting input

Career capital does not accumulate passively.
It requires a lightweight, consistent practice to convert experience into leverage.

---

## 3. Weekly Review Structure

The weekly review consists of five core questions.

Estimated time: 15 minutes.

These five questions are the complete review.
They should not expand into a lengthy planning ritual.

---

### Question 1: Application Pipeline Status

What is the current state of my active opportunities?

The system should surface:
- opportunities by lifecycle state
- how long each has been in its current state
- any stale opportunities that need a decision (advance, pause, close)

The goal is a 2-minute pipeline health check.
Not a full review of every open opportunity.

---

### Question 2: Follow-Ups Due

Who should I follow up with this week?

The system should surface:
- contacts who have not been interacted with in over a user-configured threshold (default: 60 days) and are connected to active opportunities
- any pending referral confirmations
- any outstanding recruiter or hiring manager communications

The goal is preventing relationship or application atrophy through inaction.

---

### Question 3: Skills or Gaps Noticed This Week

Did I encounter something at work this week that revealed a skill gap or a new capability?

This is a free-form prompt.
The user may answer with a few sentences or bullet points.

The system should parse this input for:
- new skill signals (something the user demonstrated or developed)
- gap signals (something the user encountered that they want to address)
- profile update candidates (new responsibilities, tools used, methods applied)

Diary ingestion from this field feeds the profile update suggestion engine.

---

### Question 4: Wins to Document

What did I accomplish this week that could become a future resume bullet or interview story?

This is one of the highest-leverage inputs in the system.

Most professionals lose professional evidence because they never capture it at the time.
By the time they update their resume, they have forgotten the specific metrics, the context, and the outcome.

Weekly win capture solves this by collecting raw evidence continuously.

The user should log:
- a brief description of the win
- any associated metric if available (even an estimate)
- the context or project

The system should store this as a raw evidence entry in the memory graph (DOC 03).
It does not need to be a polished bullet at capture time.
It becomes retrievable evidence for future tailoring, bullet generation, and interview preparation.

---

### Question 5: Market Signals Noticed

Did I notice anything this week about hiring trends, companies, or roles worth tracking?

This is a lightweight market intelligence input.

Examples:
- a company announced a new product direction that creates a relevant PM opportunity
- a role type appeared in multiple job postings that week
- a former colleague got hired into a role that signals market demand
- a company closed a funding round and is likely to expand headcount

These observations should feed:
- opportunity targeting adjustments
- company watchlist updates
- market intelligence context for future JD scoring

---

## 4. Habit Loop Design

The weekly review follows a three-part habit loop structure.

---

### Cue

The system sends a weekly review prompt at a user-configured time and day.

Default: Sunday evening.
Configurable: any day and time.

The cue should be:
- consistent
- low-friction
- associated with a fixed time the user can commit to

---

### Routine

The routine is the five-question structured review.

The system should make this as frictionless as possible:
- pre-populate pipeline status automatically (no manual input required)
- surface follow-up contacts automatically
- provide open-text fields for questions 3, 4, and 5

The target completion time is 15 minutes.
If the review takes longer, the system should prompt the user to continue next week rather than abandoning the habit.

Consistency matters more than completeness.

---

### Reward

After completing the review, the system should provide:

- a clarity score: a simple signal indicating pipeline health, relationship coverage, and win capture completeness
- a pipeline health summary: one-sentence status of the active opportunity pipeline
- one actionable insight: the single most important thing to act on this week, derived from the review inputs

The reward should feel useful, not gamified.

The insight should be:
- specific
- evidence-linked
- immediately actionable

Examples:
- "You have two opportunities in Considering state for over 14 days. Consider advancing or archiving them."
- "You captured a strong win this week. It maps to an existing gap in your Strategy PM narrative."
- "Company X is on your target list and a trusted contact works there. You haven't interacted with them in 78 days."

---

## 5. How Review Data Feeds the System

Weekly review inputs are not isolated.
They should feed the broader Linkright intelligence architecture.

---

### Wins → Memory Graph

Win entries from Question 4 are stored as raw evidence nodes in the canonical profile memory graph (DOC 03).

They become:
- retrievable inputs for future resume tailoring
- evidence candidates for bullet generation
- potential interview story seeds

The system should eventually surface these during tailoring runs and suggest converting accumulated wins into polished bullets.

---

### Market Signals → Opportunity Targeting

Market observations from Question 5 should:
- update the company watchlist if a company name is mentioned
- flag newly identified roles for attention if a role type is mentioned
- contribute to market intelligence context used in JD scoring and opportunity ranking

---

### Skills Noticed → Profile Update Suggestions

Skill and gap signals from Question 3 should trigger profile update suggestions.

The system should not auto-update the profile.
It should surface a suggestion in the next relevant workflow:
- "You mentioned X in a recent weekly review. Would you like to add this to your profile?"

The user approves all profile changes.

---

### Follow-Ups → Relationship Graph

Completed follow-up actions logged during the review should update:
- last_interaction_at for the relevant contact
- interaction_count
- any trust level adjustments the user chooses to make

---

## 6. Diary Ingestion

The weekly review supports free-form diary input in addition to the structured five questions.

Diary input is unstructured text.

Examples:
- notes from a project post-mortem
- observations from a difficult stakeholder conversation
- reflections on a hiring decision
- lessons from a failed initiative

The system should parse diary input for:
- achievement signals (new wins to capture)
- frustration signals (possible career trajectory or gap indicators)
- responsibility signals (new scope added to role)
- skill demonstration signals (things the user did that reveal capability)

Diary ingestion converts lived experience into structured career signal data.

It does not require polish at the time of entry.
The system handles interpretation.

---

## 7. Monthly Review

Once per month, the system should prompt a deeper reflection session.

The monthly review should cover:

- archetype fit check: does the work the user is doing this month align with their target PM or operator archetype?
- career trajectory check: is the direction of movement this month consistent with the user's medium-term career goal?
- decision engine refresh: are there any major decisions pending (offer comparisons, role transitions, geographic moves) that need structured analysis?
- evidence audit: have recent wins been captured with sufficient detail for future use?
- relationship audit: are there any high-value relationships that have gone cold?

The monthly review is longer than the weekly review.
Estimated time: 30-45 minutes.

It is not a productivity planning session.
It is a strategic career position check.

---

## 8. Review Cadence Design Principles

The operating rhythm should be:

- consistent: same time each week, minimal exceptions
- bounded: 15 minutes for weekly, 45 minutes for monthly — not open-ended reflection sessions
- actionable: each review produces at least one concrete next action
- non-punitive: missed weeks should not create catch-up anxiety; the system restarts the rhythm gracefully
- signal-preserving: the primary value is capturing signals before they decay, not generating plans

The rhythm should feel like a brief professional maintenance habit.
Not a career planning marathon.

---

## 9. Phase 2 — Ambient Intelligence

Phase 2 may introduce ambient intelligence that reduces dependence on the explicit weekly prompt.

Ambient intelligence may include:
- passive signal capture: the system monitors lightweight inputs (job title changes, company announcements) that the user has opted into
- contextual nudges: the system surfaces a relevant prompt when a specific trigger occurs (e.g. a target company posts a relevant role)
- asynchronous win capture: a lightweight daily capture mechanism that accumulates material for the weekly synthesis

Phase 2 ambient intelligence requires:
- stable integrations
- explicit user opt-in per integration
- clear observability of what the system is monitoring

Phase 2 remains deferred.

Phase 1 should establish the weekly rhythm as a reliable, trusted practice before adding ambient layers.

---

## 10. Non-Goals

This system is not:

- a task manager or daily to-do system
- a productivity tracker or time-logging system
- a habit tracker for personal behavior change
- a goal-setting framework for life optimization
- a journaling product

The operating rhythm exists for one purpose: career capital accumulation.

Every element of the review should connect directly to:
- improving positioning
- capturing evidence
- strengthening relationships
- informing opportunity decisions

Anything outside that scope belongs elsewhere.

---

## 11. Design Principles

The operating rhythm should be:

- low-friction: the cost of completing a weekly review should remain lower than the cost of skipping it
- signal-preserving: the primary value is preventing professional evidence decay
- system-connected: review outputs should flow into memory, opportunity, and relationship systems automatically
- human-owned: the user drives all decisions; the system captures and surfaces, never decides
- sustainable: the rhythm must be maintainable for months and years, not just during active job searches

---

## 12. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 04 — Opportunity Lifecycle & Workflow Architecture
- DOC 12 — Career Navigation Intelligence & Long-Term Compounding System
- DOC 25 — Relationship Graph & Network Intelligence

This document influences:
- DOC 03 — Canonical Profile & Memory Graph Architecture (wins and signals feed memory graph)
- DOC 24 — Closed-Loop Learning System (weekly win capture is the primary closed-loop signal source)
- DOC 28 — Identity Evolution & Archetype System (monthly archetype fit check feeds identity evolution)

This document should be treated as the canonical personal operating rhythm reference for Linkright.
