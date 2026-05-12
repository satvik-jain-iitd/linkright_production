# DOC 03 — Canonical Profile & Memory Graph Architecture

## 1. Purpose

This document defines how Linkright stores, organizes, evolves, and retrieves professional memory.

It specifies:

- canonical profile architecture
- layered memory structure
- evidence ingestion behavior
- fact persistence
- signal persistence
- interpretation persistence
- expression persistence
- memory relationships
- authoritative state handling
- profile versioning
- stale memory handling
- merge semantics
- retrieval metadata
- memory compaction philosophy

This document defines the memory substrate of Linkright.

It should support:
- high-quality retrieval
- explainability
- replayability
- strategic positioning
- long-term compounding intelligence
- future automation
- future agentic behavior

---

# 2. Memory Philosophy

Linkright should not behave like a chat history.

It should behave like:
- a structured professional memory graph
- a strategic career substrate
- a reusable intelligence layer

The system should preserve:
- truth
- traceability
- semantic structure
- strategic meaning
- retrieval usefulness
- operational lineage

The memory system exists to:
- reduce repeated work
- improve strategic consistency
- preserve professional evidence
- support adaptive positioning
- compound professional intelligence over time

---

# 3. Canonical Profile

The canonical profile is the authoritative representation of a user's professional identity inside Linkright.

It is not:
- a resume
- a LinkedIn export
- a generated narrative
- a single document

Instead, it is:
- a structured evolving graph
- composed of layered semantic entities
- connected through evidence and meaning

The canonical profile should remain:
- structured
- inspectable
- replayable
- strategically useful
- factually grounded

---

# 4. Layered Profile Architecture

The canonical profile uses a layered semantic structure.

## 4.1 Evidence Layer

Stores raw source material.

Examples:
- uploaded resumes
- LinkedIn exports
- PDFs
- recruiter emails
- interview notes
- diary entries
- portfolio docs
- screenshots
- certifications
- offer letters
- JD pages

Characteristics:
- source-preserving
- minimally interpreted
- timestamped
- attributable
- immutable where practical

Evidence remains available for:
- traceability
- replayability
- re-extraction
- future reinterpretation

---

## 4.2 Fact Layer

Stores confirmed or semi-confirmed factual atoms.

Facts should:
- remain strategically neutral where possible
- avoid excessive abstraction
- remain evidence-linked
- preserve confidence metadata
- preserve user confirmation state

Facts become the primary truth substrate.

Examples:

```text
Worked with engineering and support teams
```

```text
Owned onboarding workflow redesign initiative
```

```text
Created operational dashboards
```

---

## 4.3 Signal Layer

Stores reusable professional meaning.

Signals are derived from:
- facts
- recurring patterns
- accumulated evidence
- diary ingestion
- workflow history
- recruiter interactions

Signals represent:
- strategic abstractions
- professional maturity indicators
- behavioral patterns
- market-relevant professional traits

Signals should:
- remain reusable
- remain evidence-linked
- remain explainable
- support retrieval
- support positioning

---

## 4.4 Interpretation Layer

Stores strategic framing structures.

Interpretations represent:
- professional positioning
- strategic identity framing
- role-aware abstractions
- recruiter-facing semantic narratives

Interpretations are:
- contextual
- evolving
- audience-aware
- strategically adaptive

Interpretations are not final generated wording.

---

## 4.5 Expression Layer

Stores generated communication outputs.

Examples:
- resume bullets
- cover letter paragraphs
- autofill answers
- recruiter messages
- interview introductions
- proof-of-thinking snippets

Expressions are:
- contextual
- opportunity-aware
- strategically optimized
- width-sensitive
- layout-sensitive
- potentially ephemeral

But expressions may still be persisted for:
- caching
- reuse
- retrieval optimization
- successful-pattern reuse
- auditability

Expressions are not canonical truth.

---

# 5. Canonical Memory Flow

The canonical memory flow is:

```text
Evidence
→ Fact extraction
→ User confirmation
→ Fact persistence
→ Signal extraction
→ Interpretation generation
→ Expression generation
→ Artifact generation
```

Important:
- persistence should happen after confirmation where required
- generated outputs should remain traceable
- retrieval should remain explainable

---

# 6. Evidence Ingestion Philosophy

The system should support ingestion from multiple formats.

Examples:
- PDFs
- DOCX
- LinkedIn exports
- screenshots
- copied text
- recruiter emails
- notes
- diary entries
- browser captures
- structured forms

Users may provide information in highly inconsistent formats.

The system is responsible for:
- parsing
- structuring
- clarification
- ambiguity detection
- conflict detection
- normalization

The user should not be responsible for formatting information perfectly.

---

# 7. Confirmation-Centric Ingestion

The ingestion workflow is confirmation-driven.

Important principle:
The system may infer.
But persistent memory updates require user confirmation.

The system should:
- infer candidate facts
- show supporting evidence
- show conflicting evidence if present
- ask clarifying questions
- interrupt aggressively when ambiguity exists
- confirm field-by-field where needed

Persistence should happen only after:
- user review
- explicit confirmation
- ingestion completion

---

# 8. Conflict Handling

If multiple documents conflict:

The system should:
- detect the conflict
- surface all candidate values
- show exact evidence source references
- ask the user to resolve ambiguity
- prevent silent overwrite

Example:

```text
Resume A:
PM at Company X from Jan 2022

Resume B:
Senior PM at Company X from Mar 2022
```

The system should:
- surface both
- request clarification
- preserve lineage
- update canonical memory only after confirmation

---

# 9. Authoritative State

The canonical profile is the authoritative state.

Generated resumes are not authoritative.

Generated artifacts should derive from canonical memory.

The system should avoid:
- editing generated artifacts directly as source-of-truth
- fragmented profile drift
- hidden mutations

Profile updates should happen through:
- ingestion workflows
- structured edits
- confirmation flows
- controlled migrations

---

# 10. Profile Versioning

The canonical profile should support versioning.

Purpose:
- replayability
- historical tracking
- artifact lineage
- reproducibility
- rollback support

Every generated artifact should preserve:
- originating profile version
- originating opportunity
- originating retrieval context
- generation timestamp

This allows:
- regeneration
- debugging
- historical comparison
- strategic experimentation

---

# 11. Stale Memory Handling

Older profile states may become stale.

Examples:
- outdated responsibilities
- older positioning
- deprecated skills
- old interpretations
- obsolete market framing

The system should:
- preserve history
- mark stale entities
- avoid silent deletion
- maintain lineage

Stale memory should remain retrievable for:
- historical reconstruction
- replayability
- artifact regeneration

But stale entities should not dominate active retrieval.

---

# 12. Memory Compaction Philosophy

The system should avoid uncontrolled memory growth.

Long-term memory should become:
- cleaner
- more structured
- more strategically useful

The system should support:
- deduplication
- signal merging
- interpretation refinement
- expression caching
- evidence compression
- semantic clustering

However:
raw evidence should remain recoverable where practical.

The system should avoid losing:
- provenance
- traceability
- factual grounding

---

# 13. Deduplication

Professional memory naturally creates redundancy.

Examples:
- repeated resume bullets
- overlapping signals
- repeated projects
- repeated narratives
- semantically equivalent wording

The system should support:
- semantic similarity detection
- alias clustering
- duplicate detection
- merge proposals
- canonical entity selection

Deduplication should preserve:
- lineage
- evidence references
- historical retrieval paths

---

# 14. Signal Persistence

Signals are persisted at profile level.

Signals should:
- remain reusable across opportunities
- remain strategically useful
- evolve gradually over time
- remain evidence-linked

Signals should support:
- aliases
- merge lineage
- strategic metadata
- confidence metadata
- retrieval metadata

The system should distinguish:
- foundational signals
- market signals

---

# 15. Expression Persistence

Generated expressions may be persisted.

Reasons:
- caching
- retrieval optimization
- successful-pattern reuse
- artifact lineage
- performance optimization
- strategic reuse

However:
expressions should remain:
- contextual
- non-authoritative
- traceable

The system should avoid treating generated expressions as raw truth.

---

# 16. Memory Retrieval Metadata

Memory entities should preserve retrieval-oriented metadata.

Examples:
- semantic embeddings
- retrieval scores
- strategic scores
- opportunity relevance
- recency
- recruiter success metadata
- interview success metadata
- authenticity metadata
- identity consistency contribution

This metadata supports:
- hybrid retrieval
- strategic ranking
- adaptive intelligence

---

# 17. Diary Ingestion

The memory graph should support continuous professional learning ingestion.

Examples:
- daily diaries
- work reflections
- meeting notes
- interview reflections
- project updates
- networking reflections

Diary ingestion may help:
- signal extraction
- narrative refinement
- strategic positioning
- memory enrichment
- future interview preparation

Diary ingestion should remain:
- evidence-linked
- explainable
- retrievable

---

# 18. Memory Graph Relationships

The memory graph should preserve explicit relationships.

Examples:

```text
Evidence
→ supports Fact
```

```text
Fact
→ supports Signal
```

```text
Signal
→ contributes to Archetype
```

```text
Expression
→ generated from Interpretation
```

These relationships are critical for:
- explainability
- retrieval
- trust
- replayability
- strategic reasoning

---

# 19. Locked vs Editable State

Persisted canonical memory should not be silently editable.

Recommended workflow:

1. user proposes edit
2. system creates pending diff
3. system shows migration impact
4. user confirms
5. canonical profile updates
6. affected downstream artifacts may become stale

This prevents:
- hidden profile drift
- inconsistent artifacts
- silent contradictions

---

# 20. Memory Boundaries

The memory graph should not become:
- unstructured chat history
- giant text blob
- uncontrolled semantic dump

Memory should remain:
- structured
- layered
- explainable
- retrievable
- strategically useful

The memory system is an intelligence substrate.
Not a transcript archive.

---

# 21. Future Evolution

Future memory evolution may include:
- relationship graphs
- recruiter interaction memory
- networking intelligence
- organizational intelligence
- behavioral telemetry
- reputation graphs
- promotion intelligence
- career trajectory modeling
- ecosystem intelligence

These are future layers.
They should not overcomplicate phase 1.

---

# 22. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 02 — Core Ontology & Semantic Architecture

This document influences:
- DOC 04 — Opportunity Lifecycle & Workflow Architecture
- DOC 05 — Retrieval, Ranking & Strategic Intelligence System
- DOC 06 — Resume, Positioning & Artifact Generation Engine
- DOC 08 — CLI Runtime, MCP