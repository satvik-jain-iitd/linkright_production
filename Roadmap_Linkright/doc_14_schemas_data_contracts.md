# DOC 14 — Canonical Schemas, Entity Contracts & State Models

## 1. Purpose

This document defines the explicit data contracts for Linkright.

It specifies:

- core entity schemas for all primary domain objects
- profile graph structure and entity relationships
- local storage schemas (JSON/SQLite)
- cloud storage schemas (MongoDB)
- signal schema
- outcome event schema
- identity schema
- versioning and migration strategy
- schema governance rules

This document is the canonical contract layer for the system.

All implementation documents, retrieval systems, rendering pipelines, workflow engines, and agent coordination systems should conform to the schemas defined here.

---

## 2. Schema Design Philosophy

Schemas in Linkright should serve three purposes simultaneously:

- operational correctness — data behaves predictably at runtime
- strategic traceability — every entity can be traced back to source evidence
- evolvability — schemas can extend without breaking existing data

The architecture should separate:

- identity-stable fields (immutable once created)
- mutable operational fields (change through workflow)
- derived or computed fields (never stored as canonical truth)

Derived fields must always be marked as such.
They should never silently overwrite canonical facts.

---

## 3. Core Entity Type Map

The system recognizes the following primary domain entities:

- Signal
- Fact
- Evidence
- Expression
- CareerProfile
- Opportunity
- Application
- Outcome
- Identity
- Run
- Artifact

These entities form the operational graph of Linkright.

Their schemas define how the system stores, retrieves, reasons about, and generates career intelligence.

---

## 4. Evidence Schema

Evidence is the raw source substrate.

Evidence entities should be treated as immutable once ingested.

Fields:

```
id                   string      unique identifier
type                 enum        resume_pdf | linkedin_export | email | diary | screenshot | note | offer_letter | other
source_path          string      original file path or URL
ingested_at          datetime    timestamp of ingestion
content_raw          text        raw extracted text
content_normalized   text        cleaned text (whitespace, encoding normalized)
extraction_method    string      markitdown | manual | ocr | browser_capture
user_confirmed       boolean     whether user reviewed this ingestion
language             string      iso language code
stale                boolean     whether this evidence is superseded
stale_reason         string      optional — why it was marked stale
version              integer     increments on any mutation
```

Non-goals:
Evidence should not store semantic interpretations.
Interpretation begins at the Fact layer.

---

## 5. Fact Schema

Facts are confirmed or semi-confirmed factual atoms extracted from evidence.

Facts represent the primary truth substrate.

Fields:

```
id                   string      unique identifier
text                 text        the factual statement in plain language
evidence_ids         []string    IDs of evidence that support this fact
confidence           float       0.0–1.0
user_confirmed       boolean     whether user explicitly confirmed this fact
confirmation_at      datetime    when confirmed
version              integer     increments on mutation
created_at           datetime
updated_at           datetime
stale                boolean
stale_reason         string
```

Constraints:
A fact must link to at least one evidence entity.
Facts should not contain strategic framing or generated expressions.
Updating a fact should increment version and preserve the prior state in history.

---

## 6. Signal Schema

Signals are reusable strategic abstractions inferred from facts.

Signals represent professional meaning that persists across opportunities.

Fields:

```
id                       string      unique identifier
canonical_name           string      e.g. "ambiguity_handling"
aliases                  []string    alternative names for retrieval
definition               text        what this signal means professionally
source_evidence_ids      []string    evidence that supports this signal
source_fact_ids          []string    facts that support this signal
confidence               object      multi-dimensional confidence score (see below)
archetype_alignment      []string    which PM archetypes this signal supports
strategic_value          string      high | medium | low
recurrence_count         integer     how many times seen across career history
role_relevance           []string    role types where this signal is especially relevant
authenticity_score       float       0.0–1.0 — is this signal genuinely demonstrable
interview_demonstrability float      0.0–1.0 — can user tell a story for this
merge_lineage            []string    IDs of signals that were merged into this one
created_at               datetime
updated_at               datetime
stale                    boolean
```

Confidence sub-schema:

```
confidence.evidence_strength      float   0.0–1.0
confidence.recurrence_strength    float   0.0–1.0
confidence.strategic_value        float   0.0–1.0
confidence.authenticity           float   0.0–1.0
confidence.interview_demonstrability float 0.0–1.0
```

Signals should not be single-scored.
Multi-dimensional confidence enables more precise retrieval and positioning.

---

## 7. Expression Schema

Expressions are generated communication artifacts derived from facts, signals, and interpretations.

Expressions are not canonical truth.
They are contextual outputs tied to a specific opportunity and generation run.

Fields:

```
id                   string      unique identifier
type                 enum        resume_bullet | cover_letter_paragraph | autofill_answer | recruiter_message | interview_intro | networking_message
content              text        the generated expression
opportunity_id       string      the opportunity this expression was generated for
run_id               string      the generation run that produced this
source_signal_ids    []string    signals that contributed to this expression
source_fact_ids      []string    facts that contributed to this expression
character_count      integer     length of expression
width_score          float       rendered width score from layout engine (0.0–1.0)
layout_valid         boolean     whether this expression passed layout validation
user_approved        boolean     whether user accepted this expression
user_edited          boolean     whether user manually edited it
user_edited_version  text        user's modified version if edited
created_at           datetime
version              integer
```

---

## 8. CareerProfile Schema

The CareerProfile is the canonical representation of a user's professional identity.

It is not a resume.
It is the structured graph that generates resumes.

Fields:

```
id                       string
user_id                  string
full_name                string
email                    string
phone                    string
location                 string
linkedin_url             string
portfolio_url            string
total_years_experience   integer         ceiling-rounded, min 1 for experienced
summary_statement        text            current narrative summary
roles                    []Role          structured career history
education                []Education
certifications           []string
skills                   []Skill
current_archetype        string          active PM archetype
identity_version         integer         increments on identity-layer upgrade
created_at               datetime
updated_at               datetime
version                  integer
```

Role sub-schema:

```
role.id                  string
role.company             string
role.title               string
role.start_date          date
role.end_date            date | null
role.is_current          boolean
role.employment_type     enum    full_time | part_time | contract | freelance | side_project | pro_bono
role.description         text
role.fact_ids            []string
role.signal_ids          []string
```

Constraints:
The CareerProfile is authoritative.
Generated resumes derive from it.
Direct edits to generated artifacts should not mutate the canonical profile.

---

## 9. Opportunity Schema

An opportunity represents a single job or career opening lifecycle.

Fields:

```
id                   string
user_id              string
source               enum        linkedin | recruiter | referral | cold_apply | internal | other
title                string
company              string
jd_raw               text        original job description
jd_parsed            object      structured JD extraction (skills, signals, archetype)
status               enum        discovered | qualifying | applying | interviewing | offer | closed | rejected | withdrawn
fit_score            float       0.0–1.0
signal_map           []object    JD requirement → profile signal mapping
created_at           datetime
updated_at           datetime
artifacts            []string    artifact IDs associated with this opportunity
```

---

## 10. Application Schema

An application represents the operational lifecycle of applying to a specific opportunity.

Fields:

```
id                   string
opportunity_id       string
user_id              string
submitted_at         datetime | null
resume_artifact_id   string | null
cover_letter_artifact_id string | null
autofill_artifact_id string | null
channel              string      direct | recruiter | referral | portal
status               enum        draft | submitted | acknowledged | screening | interviewing | offer | rejected | withdrawn
created_at           datetime
updated_at           datetime
notes                text
```

---

## 11. Outcome Event Schema

Outcome events capture the closed-loop signal for learning.

Every application should accumulate outcome events over its lifecycle.

The outcome event stream feeds the conversion tracking system.

Fields:

```
id                   string
application_id       string
opportunity_id       string
user_id              string
event_type           enum        sent | recruiter_reply | screening_call | technical_screen | final_interview | offer_received | offer_accepted | offer_declined | rejection | ghosted
occurred_at          datetime    when the event happened
created_at           datetime    when it was recorded
notes                text        optional user notes
resume_version_id    string | null   which resume version was active at time of event
artifacts_active     []string    artifact IDs active at time of event
signal_ids_active    []string    which profile signals were featured in artifacts at this event
```

The outcome event schema is the primary input for closed-loop learning.

It enables the system to learn:
- which signals correlate with recruiter replies
- which bullets correlate with interview conversions
- which archetypes work for which company types
- which positioning held up under pushback

This data should accumulate over time and improve retrieval ranking.

---

## 12. Identity Schema

The identity schema captures the user's current professional archetype, level, and the evolution history of their positioning.

Fields:

```
id                               string
user_id                          string
current_archetype                string      e.g. "execution_heavy_pm", "ai_native_pm", "staff_pm"
current_level                    string      e.g. "mid", "senior", "staff", "director"
archetype_confidence             float       0.0–1.0
archetype_last_updated           datetime
signals_that_triggered_last_upgrade  []string    signal IDs that pushed the last upgrade
pending_suggested_upgrade        object | null   see below
upgrade_history                  []IdentityUpgradeEvent
created_at                       datetime
updated_at                       datetime
```

PendingSuggestedUpgrade sub-schema:

```
pending_suggested_upgrade.suggested_archetype    string
pending_suggested_upgrade.suggested_level        string
pending_suggested_upgrade.rationale              text
pending_suggested_upgrade.triggering_signal_ids  []string
pending_suggested_upgrade.suggested_at           datetime
pending_suggested_upgrade.user_decision          enum null | approved | deferred | rejected
pending_suggested_upgrade.decided_at             datetime | null
```

IdentityUpgradeEvent sub-schema:

```
upgrade_event.id                 string
upgrade_event.from_archetype     string
upgrade_event.to_archetype       string
upgrade_event.from_level         string
upgrade_event.to_level           string
upgrade_event.triggering_signals []string
upgrade_event.user_approved      boolean
upgrade_event.upgraded_at        datetime
```

Governance rule:
The system may suggest identity upgrades.
The system must never silently apply them.
User approval is required for every identity state change.

---

## 13. Profile Graph Structure

The canonical entity relationship graph is:

```
Evidence
→ supports → Fact
→ supports → Signal

Fact
→ supports → Signal
→ contributes to → CareerProfile.role

Signal
→ contributes to → Identity.archetype
→ aligns to → Opportunity.jd_signals
→ referenced by → Expression.source_signal_ids
→ referenced by → Outcome.signal_ids_active

Expression
→ generated from → Run
→ linked to → Opportunity
→ linked to → Application

Application
→ belongs to → Opportunity
→ accumulated → Outcome events

Outcome
→ feeds learning → Signal.recurrence_count
→ feeds learning → retrieval weights
```

This graph structure is the backbone of:
- retrieval strategy
- closed-loop learning
- identity compounding
- explainability

---

## 14. Local Storage Schema

Local storage uses two formats:

### JSON flat files

Purpose: profile state, facts, signals, identity snapshot.

Structure:

```
~/.linkright/
  profile.json          — canonical CareerProfile
  signals.json          — all Signal entities
  facts.json            — all Fact entities
  identity.json         — current Identity state
  opportunities/
    <opp_id>.json       — one file per opportunity
  applications/
    <app_id>.json       — one file per application
  outcomes/
    <opp_id>_events.json — outcome event stream per opportunity
  artifacts/
    <artifact_id>.json  — artifact metadata
  evidence/
    <evidence_id>.json  — evidence metadata (not raw file content)
```

### SQLite

Purpose: fast local querying, full-text search, retrieval indexes.

Key tables:

```
signals                 — indexed by canonical_name, archetype_alignment, strategic_value
facts                   — full-text indexed by content
expressions             — indexed by opportunity_id, type
outcome_events          — indexed by application_id, event_type
applications            — indexed by status
opportunities           — indexed by status, company, title
```

SQLite is a read index.
JSON files are canonical state.

On conflict: JSON files take precedence.

---

## 15. MongoDB Cloud Schema

MongoDB is used for:
- vector storage (embeddings)
- encrypted cloud backup of canonical profile state

MongoDB is not the source of truth.
JSON files are.

MongoDB is an optional sync target for cross-device access and semantic search.

Collections:

### signals_vectors

```
_id                  string      matches Signal.id
embedding            []float     fastembed or Jina embedding vector
canonical_name       string
archetype_alignment  []string
strategic_value      string
updated_at           datetime
```

### facts_vectors

```
_id                  string      matches Fact.id
embedding            []float
text_preview         string      first 200 chars
evidence_ids         []string
updated_at           datetime
```

### profile_snapshots

```
_id                  string      snapshot ID
user_id              string
snapshot_at          datetime
profile_json         object      full CareerProfile JSON encrypted
identity_json        object      Identity state encrypted
version              integer
```

Encryption:
Profile snapshots stored in MongoDB must be encrypted at rest.
Encryption key must be user-controlled.
Linkright should never have access to decrypted user profile data in cloud storage.

MongoDB should never store:
- evidence raw content
- PII not explicitly approved by user
- unencrypted personal identifiers

---

## 16. Versioning & Migration Strategy

### Entity versioning

Every schema entity has a `version` integer field.

On mutation:
- increment `version`
- persist prior state in a `_history` array or a separate history collection

The system should never silently overwrite canonical state.

Rollback: any entity can be restored to a prior version.

### Schema migration

Schema versions are tracked in:

```
~/.linkright/schema_version.json
```

Contents:

```
{
  "profile": 1,
  "signal": 2,
  "fact": 1,
  "identity": 1,
  "outcome_event": 1,
  ...
}
```

On startup, the system checks schema_version.json.
If a mismatch is detected, a migration is run before any workflow executes.

Migrations are additive by default.
Destructive migrations require explicit user confirmation.

---

## 17. Schema Governance Rules

### What is locked

The following fields are identity-stable and must not change type or semantic meaning after initial release:

- all `.id` fields
- Evidence.ingested_at
- Fact.evidence_ids
- Signal.source_fact_ids
- Outcome.application_id
- Outcome.event_type enum values (new values may be added; existing values must not change)
- Identity.upgrade_history entries (append-only)

### What can evolve

The following may extend across versions:

- new fields may be added to any schema (must be optional)
- enum values may gain new options
- confidence sub-schema may gain new dimensions
- role_relevance and archetype_alignment arrays may grow

### What is prohibited

- changing the semantic meaning of an existing field without a documented migration
- removing fields that are referenced by retrieval or learning systems
- collapsing Expression fields into Fact or Signal fields
- merging the Outcome schema with Application schema

---

## 18. Non-Goals

This document does not define:

- retrieval algorithms
- embedding strategies
- layout rendering logic
- LLM prompt schemas
- UI data binding
- authentication systems

Those belong to downstream implementation documents.

---

## 19. Document Dependencies

This document depends on:
- DOC 02 — Core Ontology & Semantic Architecture
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 04 — Opportunity Lifecycle & Workflow Architecture
- DOC 11 — Observability, Logging & Explainability Framework

This document influences:
- DOC 15 — Embeddings, Search, Hybrid Retrieval & Ranking Implementation
- DOC 16 — LaTeX Rendering, Layout Engine & Width Optimization Runtime
- DOC 18 — Evaluation, Benchmarking & Quality Measurement Framework
- DOC 23 — Career Decision Engine
