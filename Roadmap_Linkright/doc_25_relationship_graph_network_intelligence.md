# DOC 25 — Relationship Graph & Network Intelligence

## 1. Purpose

This document defines the relationship graph architecture, network intelligence system, and referral-tracking model for Linkright.

It specifies:

- relationship graph philosophy
- contact data model
- relationship types and trust layers
- AI suggestion engine design
- manual logging principles
- relationship intelligence queries
- referral tracking model
- integration with the opportunity lifecycle
- Phase 2 ecosystem intelligence direction
- non-goals and system boundaries

This document defines the canonical relationship intelligence layer of Linkright.

---

## 2. Core Philosophy

A relationship graph is not a contact list.

A contact list measures volume.
A relationship graph measures trust, context, and strategic proximity.

The distinction matters because:

- referrals are acts of reputation transfer, not information passing
- the strongest career opportunities increasingly flow through trusted networks, not cold applications
- weak relationships at scale create noise; strong relationships at depth create leverage

Linkright models relationships as a trust network.

The operative questions are:

- how well does this person know you?
- how much context do they have about your work?
- would they feel comfortable attaching their reputation to yours?
- what strategic proximity does this relationship create?

Volume is not the goal.
Trust density is the goal.

---

## 3. Relationship Graph Philosophy

The system should avoid optimizing for:

- connection count
- outreach volume
- mass familiarity

The system should optimize for:

- relationship depth
- trust signal quality
- strategic relevance
- referral readiness

One strong relationship with someone inside a target company is materially more valuable than fifty superficial connections.

The architecture should reflect this.

---

## 4. Contact Data Model

Each contact in the relationship graph should contain:

- contact_id
- name
- current_company
- current_role
- how_met (context of the first meaningful interaction)
- trust_level (enumerated: weak_tie / familiar / trusted / close)
- last_interaction_at (timestamp)
- interaction_count
- notes (free-form context about the relationship)
- tags (e.g. former_colleague, alumnus, recruiter, founder, ecosystem_operator)
- target_company_overlap (boolean: does this person work at a target company)
- referral_history (array of referral records)
- created_at
- updated_at

The contact object should remain lightweight.

It is not a CRM record.
It is a strategic relationship node.

---

## 5. Trust Levels

Trust levels capture relationship depth, not relationship length.

Definitions:

```text
weak_tie
```
You have interacted once or twice.
Context is minimal.
The person knows your name but not your work.

```text
familiar
```
You have had meaningful exchanges.
They understand your professional context at a surface level.
They might recognize your name in an email.

```text
trusted
```
They know your work quality.
They have context about your thinking or output.
They would likely respond positively to a referral request.

```text
close
```
Strong mutual respect and history.
High confidence they would advocate for you if asked.
```

Trust levels are user-defined.
The system may suggest updates based on interaction recency but never auto-assigns trust.

---

## 6. Relationship Types

Each contact has a primary relationship type.

Defined types:

- recruiter: hiring function, agency, or internal talent partner
- peer: operator at similar seniority level, different company
- referrer: someone who has referred or could plausibly refer the user
- hiring_manager: functional hiring decision-maker at a target company
- mentor: senior operator with advisory relationship
- ecosystem_connector: person with high network density inside a target ecosystem

Relationship types influence:
- what intelligence queries make sense for this contact
- how the system surfaces them during opportunity workflows
- what follow-up actions are strategically relevant

---

## 7. AI Suggestion Engine

The system should suggest who to connect with based on the user's career goals and target company list.

The suggestion engine should not import contacts from LinkedIn, email, or any external source.

It should generate suggestions in the form:

```text
You should build a relationship with a [role type] inside [company type or target company].
Rationale: [why this relationship type creates strategic proximity given your goals].
```

Examples:

- "Consider connecting with a PM at Series B AI startups in your target geography. This type of relationship can surface early-stage opportunities before they are posted publicly."
- "You have no relationships at Company X. A recruiter or peer contact there would materially improve your application probability."

The suggestion engine reads from:
- the user's target company list
- current relationship graph coverage
- career archetype and identity profile
- active opportunities in the pipeline

Suggestions should be:
- specific enough to be actionable
- strategic in rationale
- not generic networking advice

The system generates suggestions.
The user decides whether to act on them.

---

## 8. Manual Logging Principle

The user logs all actual connections manually.

This is a locked design decision.

Rationale:

Auto-importing contacts from LinkedIn or email creates several failure modes:
- ToS violations with external platforms
- privacy exposure of third-party contact data
- low-accuracy relationship context
- false trust inflation from shallow connections

Manual logging produces:
- higher accuracy
- better context per relationship
- user-owned data with no third-party dependency
- relationships that reflect actual trust, not inferred connection graphs

Manual logging does not mean high friction.

The system should make logging fast:
- add contact during opportunity review (e.g. "I know someone at this company")
- log interaction after a conversation with one command
- update trust level via a quick prompt

The cost of accuracy is worth the benefit.

---

## 9. Relationship Intelligence Queries

Given the relationship graph, the system should support answering questions such as:

- "Who in my network works at Company X right now?"
- "Do I have any trusted contacts who could refer me into this opportunity?"
- "Who have I not spoken to in over 90 days that I should follow up with?"
- "Which of my current contacts are hiring managers or recruiters at target companies?"
- "Who is best positioned to transfer trust into my application at this company?"

These queries are not ambient.
They are triggered by specific workflow contexts, primarily the opportunity lifecycle.

---

## 10. Referral Tracking

Referral records should track:

- referral_id
- contact_id (who referred)
- opportunity_id (for which opportunity)
- referral_type (internal_submission / direct_intro / informal_mention)
- has_referred (boolean)
- referral_requested_at
- referral_confirmed_at
- referral_outcome (pending / interview_granted / no_effect / unknown)
- trust_transfer_weight (user-estimated strength of the referral signal: weak / moderate / strong)
- notes

Trust transfer weight captures the reality that not all referrals are equal.

A referral from a close contact who is a senior operator at the target company carries more weight than a referral from a weak tie who barely knows your work.

The system should use trust_transfer_weight to help the user understand the likely strength of a referral, not just its existence.

---

## 11. Integration With Opportunity Lifecycle

This document integrates directly with DOC 04 — Opportunity Lifecycle & Workflow Architecture.

When an opportunity enters the "Considering" state, the system should surface:

- any contacts currently at that company
- trust level of those contacts
- whether a referral has been requested or obtained
- whether those contacts are recruiters, peers, or hiring managers

When an opportunity moves to "Optimizing," the system should surface:

- whether any relevant relationship has not been activated yet
- whether a referral path exists that the user has not pursued
- gap identification if no relationship exists at that company

When an opportunity is "Applied" or "Interviewing," the system should surface:

- relationship follow-up recommendations
- whether any pending referral feedback is expected

Relationship intelligence should be embedded into the opportunity workflow, not maintained as a separate disconnected system.

---

## 12. Relationship Health Signals

The system should maintain simple health signals per relationship:

- days since last interaction (staleness indicator)
- interaction frequency trend
- trust level trend (are interactions increasing depth or staying shallow?)

These signals should inform:
- follow-up recommendations during weekly review (see DOC 26)
- prompt to re-engage contacts who are connected to active opportunities

The system should not auto-send messages or auto-initiate contact on behalf of the user.

All relationship actions remain human-executed.
The system informs and suggests.

---

## 13. Phase 2 — Ecosystem Intelligence

Phase 2 may expand relationship intelligence to include:

- warm intro path analysis: identify second-degree paths to target companies through existing trusted contacts
- network gap analysis: where are the structural gaps in the user's current network relative to their target company list?
- ecosystem density mapping: which ecosystems (e.g. AI startups, fintech, Series B) does the user have strong versus weak representation in?
- referral probability scoring: given trust level, relationship type, and interaction history, how likely is this contact to refer?

Phase 2 remains deferred.

Phase 1 should establish a clean, manually maintained, trust-accurate relationship graph before adding analytical layers.

---

## 14. Non-Goals

This system is not:

- a CRM with pipeline stages, deal tracking, or follow-up automation
- a social graph scraper or LinkedIn data importer
- a mass outreach automation tool
- a contact enrichment service
- an email or message integration layer
- a public reputation or follower tracker

The relationship graph tracks one thing: trusted relationships that create strategic career proximity.

Everything outside that scope belongs elsewhere.

---

## 15. Design Principles

The relationship graph should remain:

- private: user-controlled, locally stored, never synced to third parties without explicit opt-in
- accurate: manual input produces better signal than auto-imported noise
- minimal: only fields that drive strategic decisions are stored
- actionable: every stored relationship should have a clear strategic purpose in the context of career navigation
- observable: the user should always understand why the system surfaces a contact in a given context

---

## 16. Storage

Relationship data follows the broader Linkright storage architecture.

Local storage is the default.
Optional encrypted cloud sync (MongoDB) is available for cross-device access.

No relationship data should be transmitted to any third-party service without explicit user consent.

Referral history, trust levels, and interaction notes are among the most sensitive data in the system.
They must be treated accordingly.

---

## 17. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 02 — Core Ontology & Semantic Architecture
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 04 — Opportunity Lifecycle & Workflow Architecture
- DOC 12 — Career Navigation Intelligence & Long-Term Compounding System

This document influences:
- DOC 26 — Personal Operating Rhythm (weekly relationship follow-up loop)
- DOC 28 — Identity Evolution & Archetype System (ecosystem positioning signals from relationship context)

This document should be treated as the canonical relationship graph and network intelligence reference for Linkright.
