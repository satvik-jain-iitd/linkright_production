# DOC 05 — Retrieval, Ranking & Strategic Intelligence System

## 1. Purpose

This document defines how Linkright retrieves, ranks, evaluates, and strategically selects professional evidence.

It specifies:

- retrieval philosophy
- retrieval pipeline architecture
- structured filtering
- semantic retrieval
- signal-first retrieval
- strategic scoring
- ranking systems
- identity consistency handling
- negative filtering
- retrieval explainability
- adaptive learning
- retrieval caching
- future reinforcement systems

This document defines the intelligence core of Linkright.

---

# 2. Retrieval Philosophy

Linkright is not solving a generic semantic search problem.

The system is solving:

```text
Find the strongest strategically useful and factually defensible professional evidence for a specific opportunity.
```

This distinction is critical.

The system should not simply retrieve:
- semantically similar text
- keyword overlap
- nearest embeddings

Instead, retrieval should optimize for:
- strategic leverage
- factual defensibility
- recruiter clarity
- identity consistency
- opportunity relevance
- interview survivability
- signal coherence

Retrieval quality is one of the core differentiators of Linkright.

---

# 3. Core Retrieval Principles

The retrieval system should:

- remain explainable
- remain strategically grounded
- remain evidence-linked
- preserve identity consistency
- avoid semantic drift
- avoid random signal scatter
- support aggressive but defensible reframing
- support replayability
- support observability

The retrieval system should avoid:
- uncontrolled RAG behavior
- giant unfiltered context dumps
- weakly grounded generation
- retrieval opacity
- contradictory positioning

---

# 4. Retrieval Objectives

The retrieval system should help the system:

- tailor resumes
- tailor cover letters
- generate autofill responses
- prepare interview answers
- generate recruiter messaging
- identify missing signals
- rank opportunities
- identify positioning gaps
- support strategic reframing
- maintain coherent professional identity

---

# 5. Retrieval Architecture

The recommended architecture is:

```text
Opportunity Analysis
→ Structured Pre-Filtering
→ Signal Identification
→ Signal Retrieval
→ Fact Retrieval
→ Semantic Ranking
→ Strategic Scoring
→ Expression Generation
→ Validation
```

This is a hybrid retrieval system.

It combines:
- deterministic filtering
- semantic retrieval
- strategic reasoning
- constrained generation

---

# 6. Opportunity Analysis

Retrieval begins with opportunity analysis.

The system should analyze:
- JD
- company
- company stage
- seniority
- domain
- role type
- strategic expectations
- technical expectations
- PM archetype alignment
- leadership expectations
- recruiter language

The output becomes a structured target profile.

Example:

```text
Target archetype:
AI-native enterprise PM

Priority signals:
- systems thinking
- ambiguity handling
- workflow orchestration

Negative signals:
- support-heavy execution
```

This analysis constrains downstream retrieval.

---

# 7. Structured Pre-Filtering

Before semantic retrieval, the system should reduce the candidate search space.

Examples of structured filtering:
- PM-only experiences
- onboarding-related projects
- AI-related work
- enterprise workflows
- growth-related projects
- startup experiences
- senior-level evidence

Structured filtering improves:
- retrieval precision
- explainability
- strategic coherence
- latency
- generation quality

The system should avoid blind global retrieval.

---

# 8. Signal-First Retrieval

Signal-first retrieval is a foundational Linkright principle.

The system should retrieve:
- signals first
- supporting evidence second

Example:

Opportunity requires:
- systems thinking
- ambiguity handling
- stakeholder leadership

The system should first identify:
- strongest matching signals

Then:
- retrieve supporting facts
- retrieve supporting interpretations
- retrieve supporting expressions

This helps maintain:
- identity consistency
- strategic coherence
- recruiter readability

---

# 9. Fact Retrieval

Facts are retrieved to ground generated outputs.

Fact retrieval should optimize for:
- relevance
- evidence strength
- recency where useful
- strategic usefulness
- interview defensibility

Fact retrieval should avoid:
- weakly grounded abstractions
- unsupported claims
- semantically distant evidence

Facts remain the primary grounding layer.

---

# 10. Semantic Retrieval

Semantic retrieval may use:
- embeddings
- vector similarity
- semantic ranking
- contextual similarity
- embedding clustering

Semantic retrieval should operate inside constrained candidate spaces.

The system should avoid:
- unconstrained embedding retrieval
- global semantic search without filtering

Semantic retrieval is a ranking tool.
Not the entire intelligence system.

---

# 11. Strategic Scoring

After retrieval, candidates should receive strategic scores.

Possible scoring dimensions:

- strategic fit
- recruiter clarity
- authenticity confidence
- identity consistency contribution
- interview defensibility
- opportunity relevance
- PM archetype alignment
- signal density
- width efficiency
- ATS usefulness
- AI-smell risk
- semantic redundancy
- seniority signaling

Strategic scoring is one of the core intelligence layers of Linkright.

---

# 12. Identity Consistency

Identity consistency is more important than maximizing random signal density.

The retrieval system should prefer:
- coherent positioning
- reinforcing signals
- strategically aligned narratives

The system should avoid:
- fragmented identities
- contradictory emphasis
- opportunistic signal scattering

Example:

A resume should not simultaneously over-emphasize:
- operational support work
- executive strategy leadership
- deep engineering ownership
- growth experimentation

unless a coherent identity supports it.

---

# 13. Negative Filtering

The retrieval system should support negative filtering.

Examples:
- avoid overly support-heavy wording
- avoid junior framing
- avoid low-leverage operational emphasis
- avoid excessive project fragmentation
- avoid contradictory archetypes

Negative filtering helps:
- maintain positioning clarity
- improve recruiter perception
- reduce narrative noise

---

# 14. Retrieval Explainability

Retrieval should remain explainable.

The system should be able to explain:
- why a fact was selected
- why a signal was prioritized
- why another candidate was rejected
- which strategic objective was served
- which retrieval stage contributed

Example:

```text
Selected because:
- strongly supports ambiguity handling
- enterprise onboarding relevance
- high recruiter clarity
- strong AI workflow alignment
```

Retrieval explainability is critical for:
- trust
- debugging
- iteration
- user confidence

---

# 15. Retrieval Candidates

Retrieval candidates may include:

- facts
- signals
- interpretations
- prior expressions
- successful resume bullets
- interview stories
- recruiter-approved messaging
- diary-derived insights

Candidates should preserve:
- provenance
- retrieval metadata
- strategic metadata
- historical outcomes where available

---

# 16. Expression Generation Constraints

Generation should happen after retrieval and scoring.

The generation system should operate within constrained semantic space.

This helps:
- reduce hallucination
- improve coherence
- improve defensibility
- improve replayability

Generation should not search memory blindly.

---

# 17. Width and Layout Awareness

Retrieval should remain aware of downstream layout constraints.

Examples:
- one-line bullet targets
- dense strategic summaries
- section balance
- space optimization

The retrieval system may prefer:
- semantically dense evidence
- concise strategic evidence
- high signal-per-character candidates

Retrieval and layout systems should cooperate.

---

# 18. Strategic Reframing

The retrieval system should support aggressive but defensible reframing.

Meaning:
- same experience may be positioned differently
- different opportunities may emphasize different signals
- expressions may vary significantly

However:
- grounding must remain traceable
- interpretations must remain defensible
- factual integrity must remain preserved

---

# 19. Confidence Systems

Retrieval should preserve confidence metadata.

Examples:
- evidence confidence
- interpretation confidence
- signal confidence
- semantic relevance confidence
- recruiter-fit confidence
- interview-defensibility confidence

Confidence should help:
- ranking
- observability
- user review
- approval workflows

Low confidence should not necessarily block generation.

Sometimes:
- strategically useful placeholders
- tentative positioning
- inferred opportunities

may still be valuable.

But confidence visibility remains important.

---

# 20. Retrieval Caching

The system may cache:
- prior retrievals
- successful expressions
- strategic rankings
- retrieval chains
- optimized bullets
- successful interview stories

Caching may improve:
- latency
- consistency
- operational efficiency
- repeated opportunity handling

Caching should remain:
- explainable
- traceable
- invalidation-aware

---

# 21. Retrieval Invalidations

Some changes should invalidate prior retrievals.

Examples:
- updated profile
- corrected metrics
- new diary evidence
- changed opportunity
- revised signal interpretations
- updated PM archetype

Invalidations should preserve:
- lineage
- historical runs
- replayability

---

# 22. Retrieval Learning Loops

Future retrieval systems may learn from:
- recruiter responses
- interview progression
- offer rates
- rejection patterns
- successful bullets
- successful narratives
- hiring outcomes
- role transitions

This is a future compounding layer.

Phase 1 should prioritize:
- correctness
- observability
- strategic coherence
- replayability

before adaptive reinforcement complexity.

---

# 23. Retrieval Metrics

Potential retrieval evaluation dimensions:

- recruiter response rate
- interview conversion
- opportunity fit quality
- identity consistency
- recruiter readability
- artifact quality
- interview survivability
- signal coherence
- width efficiency
- hallucination rate
- retrieval explainability quality

Evaluation should remain multi-dimensional.

---

# 24. Hybrid Intelligence Philosophy

The retrieval system should combine:
- deterministic filtering
- semantic intelligence
- strategic reasoning
- contextual generation
- deterministic validation

Different stages may use:
- rules
- embeddings
- heuristics
- scoring systems
- LLM reasoning
- optimization loops

The architecture should use the best mechanism for each stage.

---

# 25. Future Retrieval Evolution

Future retrieval systems may include:
- graph retrieval
- relationship-aware retrieval
- behavioral retrieval
- recruiter-specific adaptation
- organization-aware retrieval
- market-aware ranking
- ecosystem-level signal analysis
- longitudinal career trajectory reasoning

These are future layers.

Phase 1 should prioritize:
- retrieval correctness
- strategic usefulness
- observability
- operational trust

---

# 26. Retrieval Boundaries

This document defines:
- retrieval semantics
- ranking philosophy
- strategic intelligence architecture
- retrieval explainability

It does not define:
- vector DB implementation
- embedding provider implementation
- orchestration implementation
- UI rendering
- deterministic layout engine internals

Those belong to later documents.

---

# 27. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 02 — Core Ontology & Semantic Architecture
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 04 — Opportunity Lifecycle & Workflow Architecture

This document influences:
- DOC 06 — Resume, Positioning & Artifact Generation Engine
- DOC 07 — Deterministic Engines & Validation Systems
- DOC 08 — CLI Runtime, MCP & Execution Layer
- DOC 09 — Browser Extension & Ambient Intelligence Layer
- DOC 11 — Observability, Logging & Explainability Framework
- DOC 12 — Career Navigation Intelligence & Long-Term Compounding System

This document should be treated as the canonical retrieval and strategic intelligence reference for Linkright.

