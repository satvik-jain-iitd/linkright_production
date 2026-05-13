# Linkright — Documentation Architecture Master Plan

## Purpose

This document defines how Linkright architecture knowledge should be split across multiple canonical documents/canvases.

Goals:
- avoid context-window collapse
- avoid giant monolithic specs
- preserve architectural clarity
- support progressive refinement
- support future AI-assisted retrieval
- support deterministic implementation
- maintain stable canonical references
- allow independent evolution of subsystems

This is NOT the implementation spec itself.
This is the documentation topology.

---

# Documentation Philosophy

Each document should satisfy ALL of the following:

1. Single responsibility
2. Stable boundaries
3. Minimal overlap
4. Strong internal cohesion
5. Human-readable
6. AI-retrieval-friendly
7. Incrementally evolvable
8. Independently versionable
9. Runnable implementation guidance where needed
10. Explicit assumptions + dependencies

Documents should behave like:
- architectural modules
- ontology layers
- execution contracts

NOT random notes.

---

# Recommended Top-Level Documentation Structure

The system should initially be split into 12 primary canonical documents.

These documents together become the authoritative architecture specification for Linkright.

---

# DOC 01 — Vision, Philosophy & System Principles

Purpose:
Define what Linkright fundamentally is.

Contents:
- product philosophy
- career navigation definition
- strategic positioning
- AI philosophy
- epistemic integrity principles
- human augmentation principles
- copilot vs agent philosophy
- observability philosophy
- deterministic + LLM hybrid philosophy
- identity consistency principles
- strategic leverage principles
- what Linkright refuses to do
- long-term vision
- system evolution phases

Key importance:
This becomes the root philosophical reference.

---

# DOC 02 — Core Ontology & Semantic Architecture

Purpose:
Define the conceptual language of the system.

Contents:
- evidence
- facts
- signals
- interpretations
- generated expressions
- competencies
- PM archetypes
- opportunity
- workflow
- artifact
- run
- retrieval candidate
- strategic positioning
- identity consistency
- market signals vs foundational signals
- aliases
- merge semantics
- ontology evolution rules

This document defines:
"What entities exist in Linkright?"

---

# DOC 03 — Canonical Profile & Memory Graph Architecture

Purpose:
Define user memory architecture.

Contents:
- layered profile model
- canonical profile schema
- memory graph structure
- evidence ingestion rules
- fact extraction rules
- signal extraction rules
- interpretation layer rules
- expression storage rules
- memory persistence rules
- stale memory handling
- merge workflows
- deduplication
- vector embeddings
- semantic retrieval metadata
- profile versioning
- authoritative state rules

This becomes:
The memory substrate specification.

---

# DOC 04 — Opportunity Lifecycle & Workflow Architecture

Purpose:
Define opportunity-centric orchestration.

Contents:
- opportunity schema
- lifecycle states
- sub-workflows
- tags
- workflow transitions
- workflow contracts
- event model
- orchestration boundaries
- retry semantics
- replayability
- approval checkpoints
- async processing
- automation sequencing
- state transition rules
- workflow dependency graphs

This becomes:
The operational backbone of Linkright.

---

# DOC 05 — Retrieval, Ranking & Strategic Intelligence System

Purpose:
Define how intelligence retrieval works.

Contents:
- retrieval pipeline
- structured filtering
- vector search
- signal-first retrieval
- strategic scoring
- negative filtering
- recruiter-fit scoring
- identity consistency scoring
- authenticity scoring
- width efficiency scoring
- semantic ranking
- retrieval explainability
- retrieval caching
- adaptive retrieval learning
- future reinforcement loops

This becomes:
The intelligence core specification.

---

# DOC 06 — Resume, Positioning & Artifact Generation Engine

Purpose:
Define generation systems.

Contents:
- resume generation architecture
- cover letter generation
- autofill generation
- interview-prep generation
- recruiter messaging generation
- expression generation rules
- strategic reframing rules
- ATS optimization
- signal balancing
- bullet generation constraints
- width optimization integration
- one-line bullet optimization
- layout optimization
- artifact lineage
- artifact reproducibility
- placeholder systems
- metrics handling

This becomes:
The artifact rendering specification.

---

# DOC 07 — Deterministic Engines & Validation Systems

Purpose:
Define non-LLM infrastructure.

Contents:
- width calculation
- line fitting
- PDF rendering
- LaTeX orchestration
- layout optimization
- scoring engines
- deduplication systems
- semantic similarity engines
- retry systems
- cache systems
- deterministic validators
- AI-smell detection
- artifact validation
- constraint solving
- geometry/layout rules

This becomes:
The deterministic systems specification.

---

# DOC 08 — CLI Runtime, MCP & Execution Layer

Purpose:
Define the execution runtime.

Contents:
- CLI architecture
- command contracts
- execution model
- MCP architecture
- tool exposure
- local-first philosophy
- run artifacts
- execution contexts
- command lifecycle
- provider orchestration
- environment handling
- local cache handling
- replay execution
- agent interoperability
- execution tracing
- future autonomous execution hooks

This becomes:
The runtime/execution specification.

---

# DOC 09 — Browser Extension & Ambient Intelligence Layer

Purpose:
Define contextual augmentation surfaces.

Contents:
- extension architecture
- DOM detection
- contextual overlays
- ATS integrations
- LinkedIn integrations
- Gmail overlays
- autofill systems
- page-context extraction
- contextual retrieval
- contextual AI surfaces
- approval systems
- browser automation boundaries
- future ambient-agent model
- contextual memory injection

This becomes:
The ambient intelligence specification.

---

# DOC 10 — n8n Orchestration & Automation Architecture

Purpose:
Define orchestration infrastructure.

Contents:
- orchestration philosophy
- workflow boundaries
- event triggers
- queue systems
- retry policies
- scheduled automations
- webhook contracts
- workflow chaining
- async orchestration
- automation observability
- approval gating
- future autonomous workflows
- external integrations
- Gmail workflows
- Apollo/Clay integrations
- browser automation orchestration

Important principle:
n8n orchestrates.
Core intelligence stays inside Linkright runtime.

---

# DOC 11 — Observability, Logging & Explainability Framework

Purpose:
Define system transparency.

Contents:
- workflow logs
- execution traces
- retrieval rationale
- model usage logs
- scoring explanation
- artifact lineage
- decision explainability
- replayability
- debugging architecture
- audit trails
- observability schema
- user-facing transparency
- confidence systems
- human overrides
- approval logs
- telemetry philosophy

This becomes:
The trust infrastructure specification.

---

# DOC 12 — Career Navigation Intelligence & Long-Term Compounding System

Purpose:
Define long-term career intelligence.

Contents:
- career trajectory systems
- role transition systems
- PM archetype evolution
- post-offer navigation
- onboarding systems
- promotion systems
- networking intelligence
- reputation systems
- relationship graph
- learning systems
- daily diary ingestion
- proof-of-thinking systems
- personal operating systems
- strategic positioning evolution
- ecosystem navigation
- career decision engines
- long-term leverage compounding

This becomes:
The long-term career intelligence specification.

---

# Documentation Dependency Hierarchy

Recommended dependency order:

01 → philosophy
02 → ontology
03 → memory graph
04 → workflows
05 → retrieval
06 → generation
07 → deterministic systems
08 → runtime layer
09 → extension layer
10 → orchestration layer
11 → observability
12 → long-term compounding

This order matters.

---

# Important Documentation Rules

## Rule 1 — No Business Logic Duplication

Logic should exist canonically in ONE document.
Other docs reference it.

---

## Rule 2 — Documents Must Be AI Retrieval Friendly

Avoid:
- giant prose walls
- duplicated concepts
- inconsistent terminology

Prefer:
- explicit sections
- stable naming
- schema examples
- references
- deterministic terminology

---

## Rule 3 — Each Document Should Eventually Have:

- philosophy
- goals
- assumptions
- entities
- workflows
- schemas
- edge cases
- future evolution notes
- implementation guidance
- unresolved questions

---

## Rule 4 — Stable IDs For Important Concepts

Examples:
- SIG_014
- OPP_STATE_003
- RETRIEVAL_PIPELINE_V1
- ARTIFACT_CLASS_RESUME

This will help future retrieval and orchestration.

---

## Rule 5 — Distinguish Clearly Between:

- conceptual layer
- operational layer
- implementation layer

Many systems fail because these get mixed.

---

# Recommended Immediate Next Documentation Order

Start documenting in this exact order:

1. DOC 01 — Philosophy & Principles
2. DOC 02 — Ontology
3. DOC 03 — Canonical Profile & Memory Graph
4. DOC 04 — Opportunity Lifecycle
5. DOC 05 — Retrieval System

These five define the core architecture.

Everything else depends on them.

---

# Recommended Future Additional Documents

Possible future docs:

- security/privacy architecture
- model orchestration architecture
- evaluation framework
- browser automation systems
- autonomous agent governance
- recruiter intelligence systems
- social/network automation systems
- AI-native PM benchmarking
- organizational influence intelligence
- ecosystem graph analytics

These should NOT be added initially.

---

# Final Recommendation

Do NOT attempt to fully complete all documentation before implementation.

Instead:
- define contracts
- stabilize terminology
- implement vertical slices
- refine documents continuously
- let architecture evolve with operational learnings

The documentation system should behave like:
- a living architectural operating system
NOT
- static specification PDFs.

