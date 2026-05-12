# DOC 02 — Core Ontology & Semantic Architecture

## 1. Purpose

This document defines the conceptual language of Linkright.

It answers:

- what entities exist in the system
- how those entities relate to one another
- what semantic layers the architecture preserves
- how professional meaning is represented
- how strategic reasoning remains grounded in evidence

This document is not an implementation specification.
It is the semantic foundation of the system.

The ontology defined here should guide:
- memory architecture
- retrieval architecture
- generation systems
- workflow systems
- observability systems
- future agentic behavior

---

# 2. Ontology Philosophy

Linkright is not a text-generation system.
It is a professional intelligence system.

That means the architecture must preserve:

- truth
- meaning
- strategic interpretation
- communication intent
- execution traceability

The ontology exists to prevent:
- semantic collapse
- hallucination drift
- uncontrolled reinterpretation
- inconsistent positioning
- fragmented identity
- opaque reasoning

The system should preserve explicit separation between:
- evidence
- facts
- signals
- interpretations
- generated expressions

These are different semantic layers.
They must not be merged carelessly.

---

# 3. Core Semantic Layers

Linkright uses a layered semantic model.

## 3.1 Evidence Layer

Purpose:
Store raw source material.

Examples:
- resumes
- LinkedIn exports
- PDFs
- JD pages
- recruiter emails
- interview notes
- diary entries
- portfolio documents
- certifications
- proof-of-work artifacts
- uploaded screenshots

Characteristics:
- immutable where possible
- source-preserving
- timestamped
- attributable
- traceable
- minimally interpreted

Evidence is the grounding substrate.

Evidence does not represent truth directly.
It represents source material from which truth may later be inferred.

Example:

```text
"Worked with support and engineering to improve onboarding issue workflows"
```

At this layer, the system does not yet infer:
- leadership
- ambiguity handling
- systems thinking
- PM maturity

Those come later.

---

## 3.2 Fact Layer

Purpose:
Store confirmed or semi-confirmed factual atoms.

Facts are extracted from evidence.

Examples:

```text
Worked with engineering and support teams
```

```text
Owned onboarding workflow redesign initiative
```

```text
Created dashboards for operational monitoring
```

Characteristics:
- grounded in evidence
- low abstraction
- human-confirmable
- version-aware
- confidence-scored
- retrieval-friendly

Facts should remain:
- strategically neutral where possible
- minimally embellished
- semantically stable

Facts should not contain:
- exaggerated positioning
- recruiter optimization
- high-level abstractions
- executive framing

The fact layer is the primary truth substrate.

---

## 3.3 Signal Layer

Purpose:
Represent professional meaning inferred from facts.

Signals are reusable strategic abstractions.

Examples:
- ambiguity handling
- systems thinking
- execution reliability
- stakeholder management
- AI-native workflow thinking
- operational leadership
- prioritization maturity
- strategic communication
- cross-functional alignment
- founder compatibility

Signals are not raw truth.
Signals are strategic interpretations of patterns.

Characteristics:
- reusable across opportunities
- role-relevant
- strategically meaningful
- evidence-linked
- confidence-scored
- evolving over time

One fact may support many signals.
One signal may be supported by many facts.

Signals are foundational to:
- retrieval
- positioning
- scoring
- resume generation
- interview prep
- archetype mapping

---

## 3.4 Interpretation Layer

Purpose:
Represent higher-order strategic framing.

Interpretations are context-aware professional narratives derived from signals.

Examples:

```text
Cross-functional operational leadership under ambiguity
```

```text
AI-native PM with workflow orchestration intuition
```

```text
Execution-heavy enterprise product operator
```

Interpretations:
- are contextual
- are audience-aware
- may vary by target role
- may vary by company type
- may evolve over time

Interpretations are not final wording.
They are semantic positioning structures.

They help the system reason about:
- identity consistency
- role fit
- narrative coherence
- recruiter perception
- strategic framing

---

## 3.5 Expression Layer

Purpose:
Represent generated communication artifacts.

Examples:
- resume bullets
- cover letter paragraphs
- autofill answers
- recruiter responses
- interview intros
- networking messages
- proof-of-thinking summaries

Expressions are:
- highly contextual
- audience-specific
- width-sensitive
- style-sensitive
- layout-sensitive
- strategically optimized

Expressions are not canonical truth.

They are generated outputs optimized for communication.

Multiple expressions may derive from:
- the same facts
- the same signals
- the same interpretations

This separation is critical.

---

# 4. Relationship Between Layers

The canonical semantic flow is:

```text
Evidence
→ Facts
→ Signals
→ Interpretations
→ Expressions
```

This flow is directional.

Higher layers should remain traceable back to lower layers.

This allows:
- explainability
- debugging
- trust
- defensibility
- replayability
- strategic adaptation

The system should never permanently collapse upper layers into lower layers.

Generated expressions should not overwrite facts.
Interpretations should not silently rewrite evidence.

---

# 5. Signals

## 5.1 Purpose of Signals

Signals are one of the core semantic primitives of Linkright.

Signals represent reusable professional meaning.

Signals help the system:
- retrieve strategically relevant evidence
- maintain identity consistency
- adapt positioning by opportunity
- score candidate-role alignment
- generate coherent artifacts
- support interview preparation
- model professional maturity

---

## 5.2 Signal Categories

Signals may belong to broad categories such as:

### Foundational Signals

Examples:
- systems thinking
- ambiguity handling
- prioritization maturity
- execution reliability
- stakeholder alignment

These evolve slowly.

### Market Signals

Examples:
- AI-native workflows
- agentic tooling familiarity
- prompt systems thinking
- orchestration fluency

These evolve more rapidly with market conditions.

---

## 5.3 Signal Structure

Signals should generally contain:

- canonical name
- aliases
- definition
- supporting evidence links
- supporting fact links
- confidence metadata
- strategic value metadata
- recurrence metadata
- role relevance metadata
- authenticity metadata
- demonstrability metadata
- merge lineage metadata
- created_at
- updated_at

---

## 5.4 Signal Evolution

Signals evolve in place.

The system should avoid heavy ontology versioning initially.

Instead:
- signals may gain aliases
- duplicate signals may merge
- definitions may refine
- strategic interpretations may improve

The ontology should remain flexible early in system evolution.

---

## 5.5 Signal Confidence Dimensions

Signals should not use a single confidence score.

Recommended dimensions include:

- evidence strength
- recurrence strength
- strategic value
- role relevance
- authenticity confidence
- interview demonstrability

This allows richer strategic reasoning.

---

# 6. Competencies

Competencies are broader capability clusters composed of signals.

Example:

Competency:
```text
Cross-functional leadership
```

May include signals such as:
- stakeholder management
- communication clarity
- alignment building
- operational coordination

Competencies help:
- recruiter interpretation
- PM archetype mapping
- higher-order scoring
- long-term career reasoning

Competencies are broader than signals.

---

# 7. PM Archetypes

PM archetypes represent higher-order professional identities.

Examples:
- AI-native PM
- growth PM
- execution-heavy PM
- Staff PM
- technical PM
- founder-style operator
- chief-of-staff operator
- enterprise systems PM

Archetypes are:
- role-facing
- positioning-oriented
- strategically useful
- context-dependent

Archetypes are not direct truth.
They are strategic identity constructs.

Signals support archetypes.
Archetypes do not replace signals.

---

# 8. Opportunities

An opportunity represents a single job or career opportunity lifecycle.

Examples:
- LinkedIn job
- recruiter outreach
- internal transfer opportunity
- startup founder conversation
- referral-driven role

An opportunity becomes the central operational object for:
- retrieval
- tailoring
- applications
- prep
- communication
- tracking

Opportunities accumulate:
- states
- workflows
- artifacts
- logs
- scoring
- retrieval rationale
- outcomes

---

# 9. Workflows

A workflow is a bounded operational process.

Examples:
- JD parsing
- resume tailoring
- autofill generation
- HR prep generation
- signal extraction
- retrieval scoring
- width optimization

Workflows:
- operate on ontology entities
- emit logs
- produce artifacts
- create lineage
- maintain replayability

Workflows should be:
- composable
- inspectable
- replayable
- deterministic where possible

---

# 10. Artifacts

Artifacts are generated outputs.

Examples:
- PDF resumes
- LaTeX source
- prep guides
- autofill responses
- recruiter drafts
- scoring reports
- logs
- workflow outputs

Artifacts should preserve:
- lineage
- generation context
- originating workflows
- profile references
- opportunity references
- timestamps
- retrieval references where appropriate

Artifacts are important operational outputs.

---

# 11. Runs

A run represents a concrete execution instance.

Examples:
- one resume tailoring execution
- one retrieval pass
- one optimization loop
- one autofill generation pass

Runs should preserve:
- inputs
- outputs
- workflow chain
- models used
- logs
- retrieval rationale
- validation outputs
- artifacts generated

Runs are central to observability.

---

# 12. Retrieval Candidates

A retrieval candidate represents a piece of memory considered during retrieval.

Examples:
- a fact
- a signal
- an interpretation
- a prior expression
- a previous successful bullet

Retrieval candidates should preserve:
- relevance scores
- strategic scores
- retrieval provenance
- retrieval rationale
- opportunity relevance
- semantic similarity
- identity consistency contribution

---

# 13. Identity Consistency

Identity consistency is a first-class ontology concept.

The system should avoid:
- fragmented positioning
- contradictory narratives
- excessive signal scattering
- incoherent identity presentation

The ontology should support:
- coherent archetype reinforcement
- strategically aligned retrieval
- narrative continuity
- believable positioning

Identity consistency is more important than maximizing random signal density.

---

# 14. Merge Semantics

Ontology entities may merge over time.

Examples:
- duplicate signals
- overlapping competencies
- repeated evidence
- semantically equivalent interpretations

The system should preserve:
- canonical entity
- aliases
- merge lineage
- provenance

This prevents ontology entropy.

---

# 15. Ontology Evolution

The ontology should evolve gradually.

The system may:
- propose new signals
- propose merges
- propose archetypes
- suggest refined interpretations

But:
- user trust remains important
- major ontology shifts should remain inspectable
- semantic drift should be minimized

The ontology should evolve through:
- operational usage
- retrieval outcomes
- interview outcomes
- recruiter outcomes
- diary ingestion
- accumulated evidence

---

# 16. Ontology Boundaries

The ontology defines conceptual entities.

It does NOT define:
- database schema
- implementation code
- UI layout
- orchestration details
- vector database implementation
- infrastructure specifics

Those belong to later documents.

---

# 17. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles

This document influences:
- DOC 03 — Canonical Profile & Memory Graph Architecture
- DOC 04 — Opportunity Lifecycle & Workflow Architecture
- DOC 05 — Retrieval, Ranking & Strategic Intelligence System
- DOC 06 — Resume, Positioning & Artifact Generation Engine
- DOC 11 — Observability, Logging & Explainability Framework

This document should be treated as the canonical semantic reference for Linkright.

