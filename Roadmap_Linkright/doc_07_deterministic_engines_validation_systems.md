# DOC 07 — Deterministic Engines & Validation Systems

## 1. Purpose

This document defines the deterministic infrastructure and validation systems used by Linkright.

It specifies:

- deterministic engine philosophy
- layout systems
- width calculation systems
- validation pipelines
- scoring engines
- optimization loops
- deduplication systems
- semantic validation
- replayability infrastructure
- artifact integrity systems
- AI-smell detection
- constraint systems
- deterministic orchestration boundaries

This document defines the deterministic operational substrate of Linkright.

---

# 2. Deterministic Systems Philosophy

Linkright should use deterministic systems whenever:
- precision matters
- geometry matters
- reproducibility matters
- auditability matters
- replayability matters
- strict validation matters
- workflow correctness matters

Examples:
- width measurement
- layout fitting
- PDF rendering
- schema validation
- state transitions
- logging
- retry tracking
- artifact lineage
- orchestration contracts

However:
not all optimization problems are purely deterministic.

Many high-quality outcomes may emerge from:
- deterministic validation
combined with
- semantic optimization
- iterative rewriting
- layout-aware language adaptation

The architecture should therefore support:
- deterministic systems
- semantic systems
- hybrid optimization loops

---

# 3. Deterministic Responsibilities

Deterministic systems may handle:

- width measurement
- line fitting
- section geometry
- vertical space utilization
- page overflow detection
- duplicate detection
- schema validation
- orchestration validation
- replayability tracking
- artifact lineage
- caching
- workflow state validation
- retry semantics
- deterministic scoring
- validation enforcement

Deterministic systems should remain:
- inspectable
- replayable
- predictable
- testable

---

# 4. Width Calculation Engine

Width optimization is a first-class subsystem.

The width engine should:
- measure rendered width accurately
- detect overflow
- support line-fitting optimization
- support semantic compression loops
- support layout-aware rewriting

The engine should operate on:
- actual rendered geometry
not:
- approximate character counts only

The system should support:
- font-aware measurement
- LaTeX-aware rendering validation
- spacing-aware optimization
- visual rhythm preservation

---

# 5. Line-Fitting Optimization

Line-fitting optimization should support:
- one-line bullet targets
- strategic wording replacement
- semantic compression
- recruiter readability
- signal density optimization

The optimization system may:
- shorten phrases
- restructure clauses
- reorder information
- remove redundancy
- increase semantic density
- trigger semantic rewrite loops

Line fitting should remain:
- strategically aware
- layout-aware
- readability-aware

---

# 6. Layout Optimization Engine

The layout engine should optimize:

- section balance
- whitespace usage
- vertical utilization
- visual rhythm
- density consistency
- section ordering impact
- bullet spacing
- readability

The target is not aesthetic maximalism.

The target is:

```text
Strategic information density with strong readability.
```

The layout engine should support:
- iterative optimization
- deterministic validation
- semantic rewrite cooperation

---

# 7. Geometry-Aware Optimization

Optimization should consider:

- rendered width
- rendered height
- line wrapping
- spacing economics
- section geometry
- layout balance
- visual fragmentation

Geometry should become part of the optimization process.

Meaning:
- retrieval
- generation
- validation

may all respond to layout constraints.

---

# 8. Validation Philosophy

Validation is a first-class architectural layer.

Validation should:
- prevent degradation
- preserve trust
- preserve readability
- preserve strategic coherence
- prevent silent corruption

Validation should not only check:
- syntax
- formatting

It should also evaluate:
- semantic quality
- positioning quality
- signal coherence
- layout quality
- recruiter readability

---

# 9. Validation Dimensions

Validation may include:

- width overflow
- layout overflow
- duplicate signals
- semantic redundancy
- weak signal density
- ATS keyword gaps
- recruiter readability
- identity inconsistency
- hallucination risk
- unsupported claims
- AI-smell risk
- spacing imbalance
- artifact corruption
- invalid lineage

Validation should remain multi-dimensional.

---

# 10. Validation Pipelines

Validation may happen across multiple stages.

Example:

```text
Retrieval Validation
→ Strategic Validation
→ Width Validation
→ Layout Validation
→ ATS Validation
→ Final Artifact Validation
```

Validation may trigger:
- regeneration
- rewriting
- restructuring
- compression
- retry loops

---

# 11. Hybrid Optimization Loops

Many optimization problems should support iterative loops.

Example:

```text
Generate
→ Measure
→ Validate
→ Rewrite
→ Re-measure
→ Re-validate
```

Hybrid loops may combine:
- deterministic validators
- semantic rewriting
- retrieval substitution
- layout scoring
- strategic ranking

Hybrid optimization is preferred over:
- single-pass generation

for high-quality artifact systems.

---

# 12. Semantic Deduplication

The system should support semantic deduplication.

Examples:
- repeated bullets
- overlapping signals
- semantically equivalent narratives
- repeated achievements
- redundant wording

Deduplication systems may use:
- embeddings
- semantic clustering
- deterministic heuristics
- semantic similarity scoring
- LLM-assisted interpretation

Deduplication should preserve:
- lineage
- provenance
- strategic meaning

---

# 13. Constraint Systems

The system should support explicit constraints.

Examples:

```text
Maximum:
1 page
```

```text
Target:
95% vertical utilization
```

```text
Maximum:
1-line bullets where possible
```

Constraints may include:
- geometry
- readability
- ATS thresholds
- recruiter readability
- signal density
- semantic compression
- spacing balance

Constraints should remain inspectable.

---

# 14. Scoring Engines

Deterministic and hybrid scoring engines may evaluate:

- signal density
- layout efficiency
- width efficiency
- ATS coverage
- recruiter readability
- semantic redundancy
- strategic coherence
- identity consistency
- hallucination risk
- AI-smell risk

Scoring should support:
- optimization loops
- ranking systems
- validation systems
- observability

---

# 15. AI-Smell Detection

The system should attempt to reduce:
- generic phrasing
- templated wording
- exaggerated polish
- excessive symmetry
- shallow abstraction
- obvious AI patterns

Detection may use:
- heuristic analysis
- semantic scoring
- compression analysis
- recruiter readability analysis
- phrase-pattern detection

The goal is not:
- artificial human imitation

The goal is:
- believable professional communication.

---

# 16. Replayability Infrastructure

Deterministic systems should support replayability.

Replayability should preserve:
- workflow chain
- validation chain
- scoring outputs
- optimization steps
- generation settings
- geometry state
- retrieval context
- profile version

Replayability is critical for:
- debugging
- experimentation
- trust
- evaluation

---

# 17. Artifact Integrity Systems

Artifacts should support integrity validation.

Examples:
- corrupted PDFs
- broken LaTeX renders
- missing assets
- invalid lineage
- inconsistent profile references
- stale retrieval references

Integrity systems should:
- detect corruption
- surface issues
- preserve recoverability

---

# 18. Deterministic Logging

Deterministic systems should emit structured logs.

Examples:
- validation outputs
- geometry measurements
- retry reasons
- optimization steps
- scoring outputs
- layout measurements
- rendering metadata

Logs should remain:
- replayable
- inspectable
- structured

---

# 19. Optimization Priorities

When optimization conflicts exist, the system should generally prioritize:

1. Strategic quality
2. Readability
3. Identity consistency
4. Width efficiency
5. Layout density
6. ATS coverage
7. Aesthetic polish

This hierarchy may evolve later.

---

# 20. Failure Philosophy

Validation failures should remain visible.

The system should avoid:
- silent degradation
- hidden layout corruption
- silent overflow
- invalid artifacts
- broken replayability

Failures should preserve:
- logs
- state
- retryability
- partial outputs where useful

---

# 21. Testing Philosophy

Deterministic systems should support:
- repeatable tests
- regression testing
- layout snapshot testing
- scoring validation
- geometry validation
- artifact validation
- replay testing

Deterministic systems should remain highly testable.

---

# 22. Future Deterministic Evolution

Future deterministic systems may include:
- adaptive layout engines
- recruiter-attention simulations
- eye-tracking-inspired layout scoring
- semantic compression scoring
- advanced geometry optimization
- behavioral readability scoring
- recruiter scanning simulation
- dynamic rendering optimization

These are future layers.

Phase 1 should prioritize:
- correctness
- replayability
- validation quality
- width optimization
- observability

---

# 23. Deterministic Boundaries

This document defines:
- deterministic infrastructure philosophy
- validation architecture
- optimization loops
- geometry-aware systems
- replayability infrastructure

It does not define:
- retrieval semantics
- ontology semantics
- orchestration implementation
- vector database implementation
- UI rendering implementation

Those belong to other documents.

---

# 24. Document Dependencies

This document depends on:
- DOC 01 — Vision, Philosophy & System Principles
- DOC 05 — Retrieval, Ranking & Strategic Intelligence System
- DOC 06 — Resume, Positioning & Artifact Generation Engine

This document influences:
- DOC 08 — CLI Runtime, MCP & Execution Layer
- DOC 09 — Browser Extension & Ambient Intelligence Layer
- DOC 10 — n8n Orchestration & Automation Architecture
- DOC 11 — Observability, Logging & Explainability Framework

This document should be treated as the canonical deterministic systems and validation reference for Linkright.

